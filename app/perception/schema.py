"""Pydantic models for perception, boxes, and the JSON schema Gemini must answer in.

Boxes are `(ymin, xmin, ymax, xmax)` normalized to 0..1000 of the upright frame: the layout of
Gemini's `box_2d` and of `tests/fixtures/frames/boxes.json`, so boxes from Gemini, SAM 3 and the
hand-drawn ground truth compare directly. `crop()` scales them to pixels.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.memory.schema import PerceptionContext

Box = tuple[float, float, float, float]
Relation = Literal["in", "next_to", "on", "under", "unknown"]
RELATIONS: tuple[str, ...] = ("in", "next_to", "on", "under", "unknown")  # the 0001 check
UNKNOWN_ROOM = "unknown"
NO_LANDMARK = "none"


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def iou(a: Box, b: Box) -> float:
    y0, x0 = max(a[0], b[0]), max(a[1], b[1])
    y1, x1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, y1 - y0) * max(0.0, x1 - x0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def box_from_pixels(x0: float, y0: float, x1: float, y1: float, width: int, height: int) -> Box:
    return (y0 / height * 1000, x0 / width * 1000, y1 / height * 1000, x1 / width * 1000)


def box_from_gemini(raw: object) -> Box | None:
    """`box_2d` is [ymin, xmin, ymax, xmax] on 0..1000. Clamp, tolerate swapped corners, and
    return None for anything that is not four numbers enclosing some area."""
    if not isinstance(raw, list | tuple) or len(raw) != 4:
        return None
    try:
        ya, xa, yb, xb = (min(max(float(v), 0.0), 1000.0) for v in raw)
    except (TypeError, ValueError):
        return None
    box = (min(ya, yb), min(xa, xb), max(ya, yb), max(xa, xb))
    return box if box[2] > box[0] and box[3] > box[1] else None


class Detection(BaseModel):
    """One SAM 3 instance. `item` is the demo item its prompt stands for; perceive() ignores it
    (D3: SAM 3 called a distant watch "bunch of keys") and uses only the score and the box."""

    model_config = ConfigDict(frozen=True)

    item: str
    prompt: str
    confidence: float
    box: Box


class ItemSeen(BaseModel):
    """One belonging in one frame, as Gemini placed it. `landmark` is an address
    ("room > landmark") or "none". Gemini's `box_2d` arrives as `box`; perceive() may swap in a
    tighter SAM 3 box and says which in `box_source`."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    item: str
    landmark: str
    relation: Relation = "unknown"
    in_hand: bool = False
    confidence: float
    note: str = ""
    box: Box | None = None
    box_source: Literal["gemini", "sam3"] | None = None

    @model_validator(mode="before")
    @classmethod
    def _read_box_2d(cls, data: Any) -> Any:
        """Gemini answers `box_2d`; keep it as `box`, or None when it encloses nothing."""
        if isinstance(data, dict) and "box_2d" in data:
            box = box_from_gemini(data["box_2d"])
            data = {**data, "box": box, "box_source": "gemini" if box else None}
        return data

    @field_validator("relation", mode="before")
    @classmethod
    def _unknown_relation(cls, value: object) -> object:
        return value if value in RELATIONS else "unknown"

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, value: float) -> float:
        return _clamp01(value)


class Perception(BaseModel):
    """What one frame shows, in names from `perception_context()` (the CLAUDE.md contract)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    room: str
    room_confidence: float
    landmarks_in_view: list[str] = Field(default_factory=list)
    items: list[ItemSeen] = Field(default_factory=list)

    @field_validator("room_confidence")
    @classmethod
    def _clamp(cls, value: float) -> float:
        return _clamp01(value)


def build_json_schema(context: PerceptionContext) -> dict[str, Any]:
    """The response schema for one context. Enums are sorted and nothing time-dependent goes in,
    so one context always gives the same schema (and the same bake-off cache key)."""
    addresses = sorted(lm.address for lm in context.landmarks)
    number = {"type": "number", "minimum": 0, "maximum": 1}
    item = {
        "type": "object",
        "properties": {
            "item": {"type": "string", "enum": sorted(i.item for i in context.items)},
            "note": {"type": "string"},
            "box_2d": {"type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4},
            "landmark": {"type": "string", "enum": [*addresses, NO_LANDMARK]},
            "relation": {"type": "string", "enum": list(RELATIONS)},
            "in_hand": {"type": "boolean"},
            "confidence": number,
        },
        "required": ["item", "note", "box_2d", "landmark", "relation", "in_hand", "confidence"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "room": {"type": "string", "enum": [*sorted(context.rooms), UNKNOWN_ROOM]},
            "room_confidence": number,
            "landmarks_in_view": {"type": "array", "items": {"type": "string", "enum": addresses}},
            "items": {"type": "array", "items": item},
        },
        "required": ["room", "room_confidence", "landmarks_in_view", "items"],
        "additionalProperties": False,
    }
