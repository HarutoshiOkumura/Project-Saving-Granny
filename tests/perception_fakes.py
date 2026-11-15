"""Shared fakes for the perception tests: the demo home's context and fake model answers.

Nothing here calls a network service.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.memory.schema import PerceptionContext

FRAMES = Path(__file__).parent / "fixtures" / "frames"
RESPONSES = Path(__file__).parent / "fixtures" / "responses"
ROOM = "b_school_classroom"
TABLE, CHAIR, FLOOR = (f"{ROOM} > {lm}" for lm in ("table", "chair", "floor"))

# What `perception_context` returns for the seeded home (supabase/seed.sql), in its order.
CONTEXT = PerceptionContext.model_validate(
    {
        "rooms": [ROOM, "bathroom"],
        "landmarks": [
            {"room": ROOM, "landmark": "chair", "kind": "surface"},
            {"room": ROOM, "landmark": "floor", "kind": "floor"},
            {"room": ROOM, "landmark": "table", "kind": "surface"},
        ],
        "items": [
            {"item": "bag", "looks_like": "green, green handbag with gold lettering"},
            {"item": "glasses", "looks_like": "black, black reading glasses"},
            {"item": "keys", "looks_like": "black, car key fob with a few keys on a ring"},
            {"item": "watch", "looks_like": "silver, silver wristwatch"},
            {"item": "water bottle", "looks_like": "dark blue, dark blue water bottle"},
        ],
        "beliefs": [
            {"item": "glasses", "address": TABLE, "status": "active", "minutes_ago": 12},
        ],
    }
)


def gemini_answer(
    items: list[dict[str, Any]] | None = None,
    room: str = ROOM,
    room_confidence: float = 0.95,
    landmarks_in_view: list[str] | None = None,
) -> str:
    """Gemini's JSON text, shaped like the schema asks."""
    full = [
        {
            "item": "keys",
            "note": "black key fob",
            "box_2d": [470, 347, 650, 627],
            "landmark": TABLE,
            "relation": "on",
            "in_hand": False,
            "confidence": 0.9,
        }
        | item
        for item in (items if items is not None else [{}])
    ]
    return json.dumps(
        {
            "room": room,
            "room_confidence": room_confidence,
            "landmarks_in_view": landmarks_in_view if landmarks_in_view is not None else [TABLE],
            "items": full,
        }
    )


def sam3_answer(
    *predictions: tuple[int, float, list[list[float]]], prompts: int = 5
) -> dict[str, Any]:
    """SAM 3's JSON, shaped like step 04's recorded answers: (prompt index, score, polygon)."""
    results: dict[int, list[dict[str, Any]]] = {i: [] for i in range(prompts)}
    for index, confidence, polygon in predictions:
        results[index].append({"masks": [polygon], "confidence": confidence, "format": "polygon"})
    return {
        "prompt_results": [
            {"prompt_index": i, "echo": {"prompt_index": i}, "predictions": p}
            for i, p in results.items()
        ]
    }


def rectangle(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


class FakeInteractions:
    """Stands in for `client.aio.interactions`: answers in order, records every request."""

    def __init__(self, *answers: str | BaseException | SimpleNamespace) -> None:
        self.answers = list(answers)
        self.requests: list[dict[str, Any]] = []

    async def create(self, **request: Any) -> SimpleNamespace:
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        if isinstance(answer, SimpleNamespace):
            return answer
        return SimpleNamespace(status="completed", output_text=answer)

    @property
    def client(self) -> SimpleNamespace:
        return SimpleNamespace(aio=SimpleNamespace(interactions=self))


class StatusError(Exception):
    """Like the SDK's APIStatusError: a status code and a response with headers."""

    def __init__(self, status_code: int, retry_after: str | None = None) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        headers = {"retry-after": retry_after} if retry_after else {}
        self.response = SimpleNamespace(headers=headers)
