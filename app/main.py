"""FastAPI app and routes only. Handlers stay thin: parse, call one function, return."""

import logging
from typing import Annotated

from fastapi import FastAPI, Query

from app.ask import Answer, ask
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
