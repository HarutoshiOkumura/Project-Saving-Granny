"""FastAPI app and routes only. Handlers stay thin: parse, call one function, return."""

import logging
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Query, UploadFile
from pydantic import AwareDatetime, BaseModel

from app.ask import Answer, Known, ask, snapshot
from app.auth import has_app_token, require_app_token
from app.memory.schema import Channel
from app.worker.ingest import ingest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Save It")

MAX_FRAME_BYTES = 8 * 1024 * 1024


class FrameAccepted(BaseModel):
    accepted: bool = True


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/find")
async def find(
    item: Annotated[str, Query(min_length=1, max_length=200)],
    channel: Channel = "web",
) -> Answer:
    return await ask(item, channel)


@app.get("/snapshot")
async def snapshot_route(
    with_photos: Annotated[bool, Depends(has_app_token)],
) -> list[Known]:
    """Every item's current answer and where to look, for the FaceTime agent at call start. Logs
    no questions. Photo links only for a request with the APP_TOKEN: they open private crops."""
    return await snapshot(with_photos=with_photos)


@app.post("/frames", status_code=202, dependencies=[Depends(require_app_token)])
async def frames(
    background: BackgroundTasks,
    frame: UploadFile,
    device_id: Annotated[str, Form(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")],
    captured_at: Annotated[AwareDatetime, Form()],
) -> FrameAccepted:
    """One camera JPEG. Replies at once; the models run in the background, so the phone never
    waits on them."""
    jpeg = await frame.read(MAX_FRAME_BYTES + 1)
    if len(jpeg) > MAX_FRAME_BYTES:
        raise HTTPException(413, f"frame over {MAX_FRAME_BYTES} bytes")
    if not jpeg.startswith(b"\xff\xd8\xff"):
        raise HTTPException(415, "frame must be a JPEG")
    background.add_task(ingest, jpeg, device_id, captured_at)
    return FrameAccepted()
