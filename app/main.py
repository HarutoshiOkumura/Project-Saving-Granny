"""FastAPI app and routes only. Handlers stay thin: parse, call one function, return."""

import logging
from typing import Annotated

from fastapi import FastAPI, Query

from app.ask import Answer, Known, ask, snapshot
from app.memory.schema import Channel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Save It")


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
