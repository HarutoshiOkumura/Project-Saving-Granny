"""The splat builder as a small HTTP service for the GPU machine.

    SPLAT_MODEL=mock python -m splat.server                  # a laptop, no GPU
    SPLAT_ANYSPLAT_DIR=/workspace/splat-builder/AnySplat python -m splat.server   # the GPU

It listens on 127.0.0.1 only and is reached through an SSH tunnel, so there is no public port;
set `SPLAT_TOKEN` as well when it is put behind anything else. The model is loaded once, before
the first request, and builds run one at a time.

    GET    /health                         {ok, model, gpu_name, models_loaded}
    POST   /build                          photos in, one round trip: the scene once its preview
                                           is ready (multipart `frames`, repeated)
    POST   /scenes                         {scene_id}        the same, for photos sent as taken:
    POST   /scenes/{id}/frames             {n_frames}        multipart `frames`, one or many
    POST   /scenes/{id}/build?wait=true    the scene
    GET    /scenes/{id}                    {scene_id, status, version, n_frames, error, ...}
    GET    /scenes/{id}/splat?level=preview|full   the `.spz`
    GET    /scenes/{id}/cameras            cameras.json (cameras and views in viewer axes)
    DELETE /scenes/{id}

`status` goes capturing -> building -> ready_preview (version 1) -> ready (version 2), or
failed. Photos live in memory only and are dropped when the build ends. Python 3.10 syntax.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from splat import build as builder
from splat.model import AnySplatModel, MockModel, Model

logger = logging.getLogger("splat")

MAX_FRAME_BYTES = 8 * 1024 * 1024
MAX_SCENE_FRAMES = 600  # 5 minutes at 2 a second; the build picks from them


@dataclass
class Scene:
    scene_id: str
    status: str = "capturing"
    version: int = 0
    frames: list = field(default_factory=list)
    n_frames: int = 0
    description: dict | None = None
    error: str | None = None
    created: float = field(default_factory=time.time)
    preview_ready: asyncio.Event = field(default_factory=asyncio.Event)

    def to_json(self) -> dict:
        body = {
            "scene_id": self.scene_id,
            "status": self.status,
            "version": self.version,
            "n_frames": self.n_frames,
            "error": self.error,
        }
        if self.description is not None:
            for key in ("model", "frames_used", "gaussians", "bytes", "timings_ms", "start"):
                if key in self.description:
                    body[key] = self.description[key]
        return body


@dataclass
class State:
    model: Model
    data: Path
    scenes: dict = field(default_factory=dict)
    gpu: asyncio.Lock = field(default_factory=asyncio.Lock)
    tasks: set = field(default_factory=set)


def make_model() -> Model:
    if os.environ.get("SPLAT_MODEL", "anysplat") == "mock":
        return MockModel()
    repo = Path(os.environ.get("SPLAT_ANYSPLAT_DIR", "AnySplat")).resolve()
    if not (repo / "src" / "model" / "model" / "anysplat.py").exists():
        raise SystemExit(f"AnySplat is not at {repo}; set SPLAT_ANYSPLAT_DIR or SPLAT_MODEL=mock")
    return AnySplatModel(repo, os.environ.get("SPLAT_WEIGHTS", "lhjiang/anysplat"))


def create_app(model: Model | None = None, data: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = State(
            model=model or make_model(),
            data=data or Path(os.environ.get("SPLAT_DATA", "data/scenes")),
        )
        started = time.perf_counter()
        await asyncio.to_thread(state.model.load)
        logger.info(
            "model=%s loaded ms=%d", state.model.name, (time.perf_counter() - started) * 1000
        )
        app.state.splat = state
        yield

    app = FastAPI(title="Save It splat builder", lifespan=lifespan)

    def state() -> State:
        return app.state.splat

    def check_token(authorization: str | None = Header(default=None)) -> None:
        token = os.environ.get("SPLAT_TOKEN")
        if not token:
            return
        expected = f"Bearer {token}".encode()
        if authorization is None or not secrets.compare_digest(authorization.encode(), expected):
            raise HTTPException(401, "bad or missing token", {"WWW-Authenticate": "Bearer"})

    def scene_or_404(scene_id: str) -> Scene:
        scene = state().scenes.get(scene_id)
        if scene is None:
            raise HTTPException(404, "no such scene")
        return scene

    async def read_frames(uploads: list) -> list:
        frames = []
        for upload in uploads:
            data = await upload.read(MAX_FRAME_BYTES + 1)
            if len(data) > MAX_FRAME_BYTES:
                raise HTTPException(413, f"a photo is over {MAX_FRAME_BYTES} bytes")
            if not data:
                raise HTTPException(422, "an empty photo")
            frames.append(data)
        return frames

    async def run_build(
        scene: Scene, max_frames: int, preview_gaussians: int, full_gaussians: int
    ) -> None:
        """Build `scene` on the GPU, one build at a time. Never raises: a failure is a status."""
        loop = asyncio.get_running_loop()
        frames, scene.frames = scene.frames, []  # the photos leave memory when this returns
        waited = time.perf_counter()

        def on_preview(description: dict) -> None:
            def publish() -> None:
                scene.description, scene.status, scene.version = description, "ready_preview", 1
                scene.preview_ready.set()

            loop.call_soon_threadsafe(publish)

        try:
            async with state().gpu:
                queued_ms = (time.perf_counter() - waited) * 1000
                description = await asyncio.to_thread(
                    builder.build,
                    frames,
                    state().model,
                    state().data / scene.scene_id,
                    max_frames=max_frames,
                    preview_gaussians=preview_gaussians,
                    full_gaussians=full_gaussians,
                    on_preview=on_preview,
                )
            scene.description, scene.status, scene.version = description, "ready", 2
            logger.info(
                "build scene=%s status=ready frames=%d used=%d gaussians=%d preview=%d "
                "bytes[preview=%d full=%d] queued_ms=%d ms[%s]",
                scene.scene_id,
                description["frames_received"],
                description["frames_used"],
                description["gaussians"]["full"],
                description["gaussians"]["preview"],
                description["bytes"]["preview"],
                description["bytes"]["full"],
                queued_ms,
                " ".join(f"{k}={v:.0f}" for k, v in description["timings_ms"].items()),
            )
        except builder.BuildError as exc:
            scene.status, scene.error = "failed", str(exc)
            logger.warning("build scene=%s status=failed error=%s", scene.scene_id, exc)
        except Exception as exc:  # a model or CUDA error must not take the server down
            scene.status, scene.error = "failed", f"{type(exc).__name__}: {str(exc)[:300]}"
            logger.exception("build scene=%s status=failed", scene.scene_id)
        finally:
            scene.preview_ready.set()

    def start_build(
        scene: Scene, max_frames: int, preview_gaussians: int, full_gaussians: int
    ) -> None:
        if scene.status != "capturing":
            raise HTTPException(409, f"scene is {scene.status}")
        if scene.n_frames < builder.MIN_FRAMES:
            raise HTTPException(422, f"need at least {builder.MIN_FRAMES} photos")
        scene.status = "building"
        task = asyncio.create_task(run_build(scene, max_frames, preview_gaussians, full_gaussians))
        state().tasks.add(task)
        task.add_done_callback(state().tasks.discard)

    FramesParam = Query(builder.MAX_FRAMES, ge=builder.MIN_FRAMES, le=128)
    PreviewParam = Query(builder.PREVIEW_GAUSSIANS, ge=1_000, le=5_000_000)
    FullParam = Query(builder.FULL_GAUSSIANS, ge=0, le=20_000_000)  # 0: all of them

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "scenes": len(state().scenes), **state().model.describe()}

    @app.post("/build", dependencies=[Depends(check_token)])
    async def build_now(
        frames: Annotated[list[UploadFile], File()],
        max_frames: int = FramesParam,
        preview_gaussians: int = PreviewParam,
        full_gaussians: int = FullParam,
    ) -> dict:
        """Everything in one request: send the photos, get the scene back once its preview is
        ready. The full file follows; poll `GET /scenes/{id}` for version 2."""
        scene = Scene(uuid.uuid4().hex[:12])
        scene.frames = await read_frames(frames)
        scene.n_frames = len(scene.frames)
        state().scenes[scene.scene_id] = scene
        start_build(scene, max_frames, preview_gaussians, full_gaussians)
        await scene.preview_ready.wait()
        return scene.to_json()

    @app.post("/scenes", dependencies=[Depends(check_token)])
    async def create_scene() -> dict:
        scene = Scene(uuid.uuid4().hex[:12])
        state().scenes[scene.scene_id] = scene
        return {"scene_id": scene.scene_id}

    @app.post("/scenes/{scene_id}/frames", dependencies=[Depends(check_token)])
    async def add_frames(scene_id: str, frames: Annotated[list[UploadFile], File()]) -> dict:
        scene = scene_or_404(scene_id)
        if scene.status != "capturing":
            raise HTTPException(409, f"scene is {scene.status}")
        new = await read_frames(frames)
        if scene.n_frames + len(new) > MAX_SCENE_FRAMES:
            raise HTTPException(413, f"a scene holds at most {MAX_SCENE_FRAMES} photos")
        scene.frames.extend(new)
        scene.n_frames = len(scene.frames)
        return {"n_frames": scene.n_frames}

    @app.post("/scenes/{scene_id}/build", dependencies=[Depends(check_token)])
    async def build_scene(
        scene_id: str,
        wait: bool = True,
        max_frames: int = FramesParam,
        preview_gaussians: int = PreviewParam,
        full_gaussians: int = FullParam,
    ) -> dict:
        scene = scene_or_404(scene_id)
        start_build(scene, max_frames, preview_gaussians, full_gaussians)
        if wait:
            await scene.preview_ready.wait()
        return scene.to_json()

    @app.get("/scenes/{scene_id}", dependencies=[Depends(check_token)])
    async def scene_status(scene_id: str) -> dict:
        return scene_or_404(scene_id).to_json()

    @app.get("/scenes/{scene_id}/splat", dependencies=[Depends(check_token)])
    async def scene_splat(
        scene_id: str, level: str = Query("full", pattern="^(preview|full)$")
    ) -> FileResponse:
        scene = scene_or_404(scene_id)
        if scene.version < (1 if level == "preview" else 2):
            raise HTTPException(409, f"scene is {scene.status}; {level} is not ready")
        return FileResponse(
            state().data / scene_id / f"{level}.spz",
            media_type="application/octet-stream",
            filename=f"{scene_id}-{level}.spz",
        )

    @app.get("/scenes/{scene_id}/cameras", dependencies=[Depends(check_token)])
    async def scene_cameras(scene_id: str) -> FileResponse:
        scene = scene_or_404(scene_id)
        if scene.version < 1:
            raise HTTPException(409, f"scene is {scene.status}")
        return FileResponse(state().data / scene_id / "cameras.json", media_type="application/json")

    @app.delete("/scenes/{scene_id}", dependencies=[Depends(check_token)])
    async def delete_scene(scene_id: str) -> dict:
        scene = scene_or_404(scene_id)
        if scene.status == "building":
            raise HTTPException(409, "scene is building")
        del state().scenes[scene_id]
        shutil.rmtree(state().data / scene_id, ignore_errors=True)
        return {"deleted": True}

    return app


def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    uvicorn.run(
        create_app(),
        host=os.environ.get("SPLAT_HOST", "127.0.0.1"),
        port=int(os.environ.get("SPLAT_PORT", "8900")),
        log_level="warning",
        timeout_keep_alive=120,  # a client that polls every few seconds keeps one connection
    )


if __name__ == "__main__":
    main()
