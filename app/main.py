"""FastAPI app and routes only. Handlers stay thin: parse, call one function, return."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
from pydantic import AwareDatetime, BaseModel

from app import insights, moments
from app.ask import Answer, Known, ask, snapshot
from app.auth import has_app_token, require_app_token
from app.guide import Guidance, guide_to
from app.memory.schema import Channel, Concern, LifeEvent
from app.moments import Described
from app.patterns import Patterns
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


@app.get("/guide")
async def guide_route(item: Annotated[str, Query(min_length=1, max_length=200)]) -> Guidance:
    """One step toward an item, from where the camera last saw the wearer. The FaceTime agent
    polls this while the caller walks. Logs no question."""
    return await guide_to(item)


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


# ---------------------------------------------------------------------------------------------
# Insights (docs/INSIGHTS.md): the safety loop, family tags, change from usual. APP_TOKEN only.
# ---------------------------------------------------------------------------------------------

token = [Depends(require_app_token)]


@app.post("/concerns", status_code=201, dependencies=token)
async def raise_concern(body: insights.ConcernIn) -> insights.ConcernOut:
    """The FaceTime agent heard "I fell", "help", smoke or a money request, and asked once.
    Stored for the family to answer; nothing dials 911."""
    try:
        return await insights.raise_concern(body)
    except Exception as exc:
        raise HTTPException(503, "could not store the concern") from exc


@app.get("/api/concerns", dependencies=token)
async def concern_board() -> insights.ConcernBoard:
    return await insights.concern_board()


@app.post("/api/concerns/{concern_id}/handle", dependencies=token)
async def handle_concern(concern_id: UUID, body: insights.HandleIn) -> Concern:
    concern = await insights.handle_concern(concern_id, body)
    if concern is None:
        raise HTTPException(404, "no such concern")
    return concern


@app.post("/api/events", status_code=201, dependencies=token)
async def add_event(body: insights.EventIn) -> LifeEvent:
    return await insights.add_event(body)


@app.get("/api/events", dependencies=token)
async def list_events(days: Annotated[int, Query(ge=1, le=365)] = 56) -> list[LifeEvent]:
    return await insights.list_events(days)


@app.get("/api/patterns", dependencies=token)
async def patterns(days: Annotated[int, Query(ge=7, le=182)] = 56) -> Patterns:
    """Daily facts and any change from the person's own usual. Not a medical test."""
    return await insights.patterns(days)
