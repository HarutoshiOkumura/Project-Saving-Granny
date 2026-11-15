"""FastAPI app and routes only. Handlers stay thin: parse, call one function, return."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AwareDatetime, BaseModel

from app import moments, room
from app.ask import Answer, Known, ask, snapshot
from app.auth import require_app_token
from app.memory.schema import Channel
from app.moments import Described
from app.worker.ingest import ingest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """While the backend runs, keep the moments search copy in step with Postgres."""
    refresher = asyncio.create_task(moments.keep_current())
    yield
    refresher.cancel()


app = FastAPI(title="Save It", lifespan=lifespan)

MAX_FRAME_BYTES = 8 * 1024 * 1024
WEB = Path(__file__).parent / "web"

# three.js and Spark for the room view, served from here so the page needs no other network.
app.mount("/room/lib", StaticFiles(directory=WEB / "vendor", check_dir=False), name="room-lib")


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
async def snapshot_route() -> list[Known]:
    """Every item's current answer, for the FaceTime agent at call start. Logs no questions."""
    return await snapshot()


@app.get("/describe")
async def describe(
    q: Annotated[str, Query(min_length=1, max_length=300)],
    channel: Channel = "web",
) -> Described:
    """ "The silver one I wear on my wrist": the item those words mean, answered like `/find`."""
    return await moments.describe(q, channel)


@app.get("/moments/{sighting_id}/photo", dependencies=[Depends(require_app_token)])
async def moment_photo(
    sighting_id: UUID,
    w: Annotated[int, Query(ge=160, le=1920)] = 1280,
    h: Annotated[int, Query(ge=120, le=1080)] = 720,
    safe: Annotated[str | None, Query(pattern=r"^\d{1,4}(,\d{1,4}){3}$")] = None,
) -> Response:
    """The photo of one sighting as a `w` x `h` JPEG for the FaceTime card. `safe` is
    `left,top,right,bottom` in card pixels: the part of the card the caller sees and no text
    covers. The whole photo is fitted inside it, never cut; without `safe` it fills the picture.
    `X-Item-Circle: x,y,radius` says where to ring the item."""
    left, top, right, bottom = (int(v) for v in safe.split(",")) if safe else (0, 0, w, h)
    if not (0 <= left < right <= w and 0 <= top < bottom <= h):
        raise HTTPException(422, "safe must be left,top,right,bottom inside the card")
    photo = await moments.card(sighting_id, w, h, (left, top, right, bottom))
    if photo is None:
        raise HTTPException(404, "no photo for this sighting")
    headers = {"Cache-Control": "private, no-store"}
    if photo.circle is not None:
        headers["X-Item-Circle"] = ",".join(str(v) for v in photo.circle)
    return Response(photo.jpeg, media_type="image/jpeg", headers=headers)


@app.get("/room", include_in_schema=False)
async def room_page() -> FileResponse:
    """The 3D room view (static page; its data calls carry the app token)."""
    return FileResponse(WEB / "room.html", headers={"Cache-Control": "no-cache"})


@app.get("/room/scene", dependencies=[Depends(require_app_token)])
async def room_scene() -> room.RoomScene:
    """The room scan's views and pins, and where the memory says each item is now."""
    try:
        return await room.scene()
    except room.NoScan as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/room/splat", dependencies=[Depends(require_app_token)])
async def room_splat(level: room.Level = "full") -> FileResponse:
    path = room.splat_path(level)
    if path is None:
        raise HTTPException(404, f"no {level} room scan")
    return FileResponse(
        path, media_type="application/octet-stream", headers={"Cache-Control": "private, no-store"}
    )


@app.put("/room/pins", dependencies=[Depends(require_app_token)])
async def room_pin(request: room.PinRequest) -> room.RoomPin:
    """Place a landmark's pin where a tap in the 3D view lands (`landmarks.x/y/z`)."""
    try:
        return await room.place_pin(request)
    except room.NoScan as exc:
        raise HTTPException(404, str(exc)) from exc
    except room.UnknownLandmark as exc:
        raise HTTPException(404, f"no landmark {exc}") from exc
    except room.NothingThere as exc:
        raise HTTPException(422, "that tap does not land on the scan") from exc


@app.delete("/room/pins", status_code=204, dependencies=[Depends(require_app_token)])
async def room_pin_clear(address: Annotated[str, Query(min_length=1, max_length=200)]) -> None:
    try:
        await room.clear_pin(address)
    except room.UnknownLandmark as exc:
        raise HTTPException(404, f"no landmark {exc}") from exc


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
