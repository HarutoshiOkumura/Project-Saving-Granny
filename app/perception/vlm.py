"""One frame and its context to Gemini; a `Perception` back, or None to skip the frame.

Request shape checked against the Interactions, structured output, image understanding, thinking
and media resolution docs (links in CLAUDE.md) on 14 Nov, and live in step 04. Settings are the
ones step 04 measured (D3, D24): thinking `low`, resolution `high`, no beliefs in the prompt,
sampling left at its defaults, and `store=False` on every call.
"""

import asyncio
import base64
import logging
import time
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings, get_settings
from app.memory.schema import Belief, PerceptionContext
from app.perception.retry import GiveUp, describe, with_retries
from app.perception.schema import (
    NO_LANDMARK,
    UNKNOWN_ROOM,
    Perception,
    build_json_schema,
)

logger = logging.getLogger(__name__)

THINKING_LEVEL = "low"  # step 04: `minimal` missed a keys close-up
RESOLUTION = "high"  # 1,120 tokens; `medium` was never tried at a distance

_client: tuple[asyncio.AbstractEventLoop, genai.Client] | None = None


def build_prompt(context: PerceptionContext, beliefs: list[Belief] | None = None) -> str:
    """The step 04 prompt, word for word. perceive() never passes beliefs (D3); the bake-off does,
    to measure them."""
    places = "\n".join(f"- {a}" for a in sorted(lm.address for lm in context.landmarks))
    things = "\n".join(f"- {i.item}: {i.looks_like}" for i in context.items)
    lines = [
        "You are the eyes of a memory aid for a person with dementia. This photo comes from a "
        "phone worn on a lanyard at chest height. Report which of their belongings you can see "
        "and where each one is.",
        "",
        f"Rooms: {', '.join(sorted(context.rooms))}. "
        'Use "unknown" if you cannot tell which room this is.',
        "",
        'Places, written "room > place":',
        places,
        "",
        "Belongings to look for:",
        things,
    ]
    if beliefs:
        lines += [
            "",
            "Where the belongings were last seen, from earlier photos. This may be out of date "
            "and is not evidence about this photo:",
        ]
        for b in beliefs:
            where = "in the wearer's hand" if b.in_hand else (b.address or "unknown place")
            lines.append(f"- {b.item}: {where}, {b.minutes_ago} minutes ago")
    lines += [
        "",
        "Rules:",
        "- Report a belonging only if you can see it in this photo. Never report one because it "
        "is on the list or was seen somewhere before. An empty list is a good answer.",
        "- room_confidence: from 0 to 1.",
        '- landmark: the listed place the belonging is on, in or under. Use "none" if it is not '
        "at a listed place.",
        "- relation: how it sits at that place: on, in, under or next_to; unknown if unsure.",
        "- in_hand: true only if it is in the wearer's own hand.",
        "- landmarks_in_view: every listed place clearly visible in the photo, with or without "
        "anything on it.",
        "- box_2d: a tight box around the belonging as [ymin, xmin, ymax, xmax], normalized to "
        "0-1000.",
        "- confidence: from 0 to 1. When unsure, give a lower number rather than guess.",
        "- note: a few words on what you see, such as colour and what it is next to. Never "
        "describe people.",
    ]
    return "\n".join(lines)


def build_input(jpeg: bytes, prompt: str, resolution: str = RESOLUTION) -> list[dict[str, Any]]:
    """Text first, then the image: the image doc's order for a single image."""
    return [
        {"type": "text", "text": prompt},
        {
            "type": "image",
            "data": base64.b64encode(jpeg).decode(),
            "mime_type": "image/jpeg",
            "resolution": resolution,
        },
    ]


async def look(jpeg: bytes, context: PerceptionContext) -> Perception | None:
    """Ask Gemini what one upright JPEG shows. None means skip the frame: no key, every attempt
    failed or timed out, an answer that did not complete, or one that does not parse."""
    settings = get_settings()
    started = time.perf_counter()
    request = {
        "model": settings.perception_model,
        "input": build_input(jpeg, build_prompt(context)),
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": build_json_schema(context),
        },
        "generation_config": {"thinking_level": THINKING_LEVEL},
        "store": False,
        "timeout": settings.perception_timeout_s,
    }
    try:
        text = await with_retries(
            lambda: _ask(request, settings),
            timeout_s=settings.perception_timeout_s,
            what="gemini",
        )
        perception = Perception.model_validate_json(text)
    except Exception as exc:
        logger.warning(
            "gemini skipped model=%s error=%s ms=%d",
            settings.perception_model,
            describe(exc),
            round((time.perf_counter() - started) * 1000),
        )
        return None
    return within_context(perception, context)


async def _ask(request: dict[str, Any], settings: Settings) -> str:
    """One attempt. Returns the answer's text; raises GiveUp when retrying cannot help."""
    interaction = await _get_client(settings).aio.interactions.create(**request)
    if interaction.status != "completed":
        raise GiveUp(f"status {interaction.status}")
    if not interaction.output_text:
        raise GiveUp("completed with no text")
    return interaction.output_text


def within_context(perception: Perception, context: PerceptionContext) -> Perception:
    """Constrained decoding keeps answers inside the enums; this makes sure of it, because a name
    outside them would make `log_sighting` raise. Off-list rooms become "unknown", off-list
    landmarks "none", and off-list items and places in view are dropped."""
    rooms = set(context.rooms)
    addresses = {lm.address for lm in context.landmarks}
    names = {i.item for i in context.items}
    items = [
        it if it.landmark in addresses else it.model_copy(update={"landmark": NO_LANDMARK})
        for it in perception.items
        if it.item in names
    ]
    return perception.model_copy(
        update={
            "room": perception.room if perception.room in rooms else UNKNOWN_ROOM,
            "landmarks_in_view": [a for a in perception.landmarks_in_view if a in addresses],
            "items": items,
        }
    )


def _get_client(settings: Settings) -> genai.Client:
    """One client per event loop. The SDK's own retries are off: by default it retries 408, 409,
    429 and 5xx up to 4 times inside one call, which stacked into a 429 storm in step 04."""
    global _client
    loop = asyncio.get_running_loop()
    if _client is None or _client[0] is not loop:
        if settings.google_api_key is None:
            raise GiveUp("GOOGLE_API_KEY is not set")
        client = genai.Client(
            api_key=settings.google_api_key.get_secret_value(),
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
        )
        _client = (loop, client)
    return _client[1]
