"""Step 04 detector bake-off on the staged frames in tests/fixtures/frames/.

    uv run python -m scripts.bakeoff                 # everything
    uv run python -m scripts.bakeoff --only sam3     # one family: yolo, sam3 or gemini
    uv run python -m scripts.bakeoff --full          # every Gemini comparison on every model

Inference only: nothing is uploaded to a Roboflow project, and every Gemini call passes
`store=False`. Responses are cached under `.cache/bakeoff/`, so a re-run costs nothing and reports
the latencies measured the first time. The report is printed and saved to
`.cache/bakeoff/report.md`.

Frame names carry the ground truth. Hyphens stand for spaces and underscores:
    close_<item>_<landmark>_<nn>.jpg, medium_<item>_<landmark>_<nn>.jpg
    empty_<landmark or room>_<nn>.jpg        no demo item in view
`tests/fixtures/frames/boxes.json` holds a hand-drawn box around the item in each item frame.

Scoring:
- A detector hit is a box of the right item at or above the threshold with IoU >= 0.5 against the
  hand-drawn box. Any box on an empty frame is a false alarm; a box on an item frame that is not a
  hit is an extra.
- For Gemini, the worker's drop rules run first (room cut, item cut, landmark "none" not in hand,
  one entry per item), so the counts are what would reach `log_sighting`. A hit is the right item
  stored; placed is a hit on the right landmark. Gemini's own `box_2d` is scored like a detector.
"""

import argparse
import asyncio
import base64
import hashlib
import io
import json
import math
import statistics
import sys
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx
from google import genai
from google.genai import types
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, field_validator

from app.config import get_settings
from app.memory import db
from app.memory.schema import Belief, PerceptionContext

ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = ROOT / "tests" / "fixtures" / "frames"
CACHE_DIR = ROOT / ".cache" / "bakeoff"

# What the capture page is expected to send: the long side at 1920 px, JPEG quality 85.
MAX_SIDE = 1920
JPEG_QUALITY = 85

# Worker cuts from the perception rules (D11).
ROOM_CUT = 0.6
ITEM_CUT = 0.5
IOU_HIT = 0.5

YOLO_VERSION = "v2-l"
YOLO_FLOOR = 0.05
YOLO_THRESHOLDS = (0.05, 0.1, 0.2, 0.3)
SAM3_FLOOR = 0.1
SAM3_THRESHOLDS = (0.3, 0.5, 0.7)

GEMINI_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-4-hydrogen")
NO_MINIMAL_THINKING = {"gemini-4-hydrogen"}  # thinking doc: minimal is not supported on Gemini 4
GEMINI_TIMEOUT_S = 60.0  # generous on purpose: the bake-off measures latency, it does not cut it
RELATIONS = ("in", "next_to", "on", "under", "unknown")

# Two or three wordings per item for the open-vocabulary detectors (docs/ROBOFLOW.md section 2).
WORDINGS: dict[str, dict[str, str]] = {
    "names": {
        "bag": "bag",
        "glasses": "glasses",
        "keys": "keys",
        "watch": "watch",
        "water bottle": "water bottle",
    },
    "descriptive": {
        "bag": "green handbag",
        "glasses": "eyeglasses",
        "keys": "bunch of keys",
        "watch": "wristwatch",
        "water bottle": "dark blue bottle",
    },
    "alternate": {
        "bag": "green clutch bag",
        "glasses": "reading glasses",
        "keys": "car keys",
        "watch": "silver watch",
        "water bottle": "bottle",
    },
}

# Beliefs for the with-beliefs runs, in the shape `perception_context` returns. They are chosen to
# tempt the model: every landmark in an empty frame has a believed item on it, and several item
# frames show the item somewhere other than where it is believed to be.
TEST_BELIEFS = {
    "glasses": ("table", 12),
    "keys": ("table", 40),
    "water bottle": ("chair", 5),
    "watch": ("chair", 25),
    "bag": ("floor", 8),
}

Box = tuple[float, float, float, float]  # ymin, xmin, ymax, xmax on 0..1000


# --------------------------------------------------------------------------------------------
# Frames and ground truth
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Truth:
    distance: Literal["close", "medium", "empty"]
    item: str | None  # None on empty frames
    landmark: str | None  # landmark name; None for a wide room shot
    room: str


@dataclass(frozen=True)
class Frame:
    name: str
    truth: Truth
    box: Box | None
    jpeg: bytes
    width: int
    height: int

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.jpeg).hexdigest()

    @property
    def b64(self) -> str:
        return base64.b64encode(self.jpeg).decode()


def _norm(name: str) -> str:
    return name.replace(" ", "-").replace("_", "-").lower()


def parse_name(stem: str, context: PerceptionContext) -> Truth:
    """Read the ground truth from a file name such as `close_water-bottle_table_01`."""
    parts = stem.split("_")
    landmarks = {_norm(lm.landmark): lm for lm in context.landmarks}
    if len(parts) == 3 and parts[0] == "empty":
        token = parts[1]
        if token in landmarks:
            lm = landmarks[token]
            return Truth("empty", None, lm.landmark, lm.room)
        rooms = {_norm(r): r for r in context.rooms}
        if token in rooms:
            return Truth("empty", None, None, rooms[token])
        raise ValueError(f"{stem}: {token!r} is neither a landmark nor a room")
    if len(parts) == 4 and parts[0] in ("close", "medium"):
        items = {_norm(i.item): i.item for i in context.items}
        if parts[1] not in items:
            raise ValueError(f"{stem}: unknown item {parts[1]!r}")
        if parts[2] not in landmarks:
            raise ValueError(f"{stem}: unknown landmark {parts[2]!r}")
        lm = landmarks[parts[2]]
        return Truth(parts[0], items[parts[1]], lm.landmark, lm.room)  # type: ignore[arg-type]
    raise ValueError(f"{stem}: expected close|medium_<item>_<landmark>_<nn> or empty_<x>_<nn>")


def prepare_jpeg(path: Path) -> tuple[bytes, int, int]:
    """Upright (EXIF rotation applied), long side at most MAX_SIDE, JPEG with no metadata.

    A file that already is that, as the committed fixtures are, is sent byte for byte: it is not
    compressed twice, and its cache keys match the frames it was made from.
    """
    data = path.read_bytes()
    with Image.open(io.BytesIO(data)) as raw:
        if raw.format == "JPEG" and not raw.getexif() and max(raw.size) <= MAX_SIDE:
            return data, raw.width, raw.height
        image = ImageOps.exif_transpose(raw).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue(), image.width, image.height


def load_frames(context: PerceptionContext) -> list[Frame]:
    boxes = json.loads((FRAMES_DIR / "boxes.json").read_text())
    frames = []
    paths = sorted(p for p in FRAMES_DIR.iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    for path in paths:
        truth = parse_name(path.stem, context)
        box = boxes.get(path.stem)
        if (box is None) != (truth.item is None):
            raise ValueError(f"{path.name}: boxes.json must have a box for item frames only")
        jpeg, width, height = prepare_jpeg(path)
        frames.append(Frame(path.stem, truth, tuple(box) if box else None, jpeg, width, height))
    if not frames:
        raise SystemExit(f"no frames in {FRAMES_DIR}")
    return frames


# --------------------------------------------------------------------------------------------
# Boxes
# --------------------------------------------------------------------------------------------


def iou(a: Box, b: Box) -> float:
    y0, x0 = max(a[0], b[0]), max(a[1], b[1])
    y1, x1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, y1 - y0) * max(0.0, x1 - x0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def box_from_pixels(x0: float, y0: float, x1: float, y1: float, width: int, height: int) -> Box:
    return (y0 / height * 1000, x0 / width * 1000, y1 / height * 1000, x1 / width * 1000)


def box_from_gemini(raw: list[int]) -> Box | None:
    """`box_2d` is [ymin, xmin, ymax, xmax] on 0..1000; tolerate swapped corners."""
    if len(raw) != 4:
        return None
    ya, xa, yb, xb = (min(max(float(v), 0.0), 1000.0) for v in raw)
    return (min(ya, yb), min(xa, xb), max(ya, yb), max(xa, xb))


# --------------------------------------------------------------------------------------------
# Cache and retries
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Outcome:
    response: Any  # parsed JSON, or None after an error
    latency_s: float | None
    error: str | None


RETRYABLE = {408, 429, 500, 502, 503, 504}


def _status(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return getattr(exc, "status_code", None)


RATE_LIMITED = 0  # 429 answers seen in this run; the report prints the count


def _retry_after(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None) or getattr(exc, "raw_response", None)
    value = getattr(response, "headers", {}).get("retry-after") if response else None
    try:
        return float(value) if value else None
    except ValueError:
        return None


async def call_with_retries(call: Callable[[], Awaitable[Any]], retries: int = 3) -> Outcome:
    """Time one successful attempt. Retry timeouts, network errors, 429 and 5xx with backoff.

    The clients' own retries are off, so a rate-limit wait is never counted as latency.
    """
    global RATE_LIMITED
    error = ""
    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            response = await call()
            return Outcome(response, time.perf_counter() - start, None)
        except Exception as exc:  # every failure is recorded; none stops the run
            status = _status(exc)
            error = f"{type(exc).__name__} {status or ''} {str(exc)[:200]}".strip()
            print(f"  attempt {attempt + 1} failed: {error[:120]}", file=sys.stderr)
            if status == 429:
                RATE_LIMITED += 1
            if status is not None and status not in RETRYABLE:
                break
            if attempt < retries:
                backoff = (20 if status == 429 else 2) * 2**attempt
                await asyncio.sleep(_retry_after(exc) or backoff)
    return Outcome(None, None, error)


def cache_path(kind: str, key: dict[str, Any]) -> Path:
    digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:24]
    return CACHE_DIR / kind / f"{digest}.json"


async def cached(kind: str, key: dict[str, Any], call: Callable[[], Awaitable[Any]]) -> Outcome:
    """Errors are not cached, so a re-run retries them."""
    path = cache_path(kind, key)
    if path.exists():
        saved = json.loads(path.read_text())
        return Outcome(saved["response"], saved["latency_s"], None)
    outcome = await call_with_retries(call)
    if outcome.error is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = {"key": key, "response": outcome.response, "latency_s": outcome.latency_s}
        path.write_text(json.dumps(saved))
    return outcome


# --------------------------------------------------------------------------------------------
# Roboflow detectors (inference only)
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Detection:
    item: str
    confidence: float
    box: Box


@dataclass(frozen=True)
class DetectorResult:
    frame: Frame
    detections: list[Detection] | None  # None when the call failed
    latency_s: float | None
    error: str | None


async def run_yolo(
    http: httpx.AsyncClient, frame: Frame, wording: dict[str, str]
) -> DetectorResult:
    classes = list(wording.values())
    body = {
        "text": classes,
        "yolo_world_version_id": YOLO_VERSION,
        "confidence": YOLO_FLOOR,
        "disable_model_monitoring": True,
    }

    async def call() -> Any:
        payload = {**body, "image": {"type": "base64", "value": frame.b64}}
        response = await http.post("/yolo_world/infer", json=payload)
        response.raise_for_status()
        return response.json()

    out = await cached("yolo", {**body, "image": frame.sha}, call)
    if out.response is None:
        return DetectorResult(frame, None, None, out.error)
    by_class = {v: k for k, v in wording.items()}
    detections = []
    for p in out.response.get("predictions", []):
        x, y, w, h = p["x"], p["y"], p["width"], p["height"]
        box = box_from_pixels(x - w / 2, y - h / 2, x + w / 2, y + h / 2, frame.width, frame.height)
        detections.append(Detection(by_class[p["class"]], p["confidence"], box))
    return DetectorResult(frame, detections, out.latency_s, None)


async def run_sam3(
    http: httpx.AsyncClient, frame: Frame, wording: dict[str, str]
) -> DetectorResult:
    body = {
        "prompts": [{"type": "text", "text": text} for text in wording.values()],
        "output_prob_thresh": SAM3_FLOOR,
        "format": "polygon",
        "disable_model_monitoring": True,
    }

    async def call() -> Any:
        payload = {**body, "image": {"type": "base64", "value": frame.b64}}
        response = await http.post("/sam3/concept_segment", json=payload)
        response.raise_for_status()
        return response.json()

    out = await cached("sam3", {**body, "image": frame.sha}, call)
    if out.response is None:
        return DetectorResult(frame, None, None, out.error)
    items = list(wording)
    detections = []
    for result in out.response["prompt_results"]:
        item = items[result["prompt_index"]]
        for p in result["predictions"]:
            points = [pt for polygon in p["masks"] for pt in polygon]
            if not points:
                continue
            xs, ys = [pt[0] for pt in points], [pt[1] for pt in points]
            box = box_from_pixels(min(xs), min(ys), max(xs), max(ys), frame.width, frame.height)
            detections.append(Detection(item, p["confidence"], box))
    return DetectorResult(frame, detections, out.latency_s, None)


# --------------------------------------------------------------------------------------------
# Gemini: schema, prompt and call
# --------------------------------------------------------------------------------------------


def build_schema(context: PerceptionContext) -> dict[str, Any]:
    """Enums from the context, sorted, so one context always gives the same schema."""
    addresses = sorted(lm.address for lm in context.landmarks)
    number = {"type": "number", "minimum": 0, "maximum": 1}
    item = {
        "type": "object",
        "properties": {
            "item": {"type": "string", "enum": sorted(i.item for i in context.items)},
            "note": {"type": "string"},
            "box_2d": {"type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4},
            "landmark": {"type": "string", "enum": [*addresses, "none"]},
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
            "room": {"type": "string", "enum": [*sorted(context.rooms), "unknown"]},
            "room_confidence": number,
            "landmarks_in_view": {"type": "array", "items": {"type": "string", "enum": addresses}},
            "items": {"type": "array", "items": item},
        },
        "required": ["room", "room_confidence", "landmarks_in_view", "items"],
        "additionalProperties": False,
    }


def build_prompt(context: PerceptionContext, beliefs: list[Belief] | None) -> str:
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


def tempting_beliefs(context: PerceptionContext) -> list[Belief]:
    address = {lm.landmark: lm.address for lm in context.landmarks}
    return [
        Belief(item=item, address=address[lm], status="active", minutes_ago=minutes)
        for item, (lm, minutes) in TEST_BELIEFS.items()
        if lm in address and item in {i.item for i in context.items}
    ]


class SeenItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item: str
    landmark: str
    relation: str = "unknown"
    in_hand: bool = False
    confidence: float
    box_2d: list[int] = []
    note: str = ""

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, value: float) -> float:
        return min(max(value, 0.0), 1.0)


class Seen(BaseModel):
    model_config = ConfigDict(extra="ignore")

    room: str
    room_confidence: float
    landmarks_in_view: list[str]
    items: list[SeenItem]


@dataclass(frozen=True)
class GeminiConfig:
    model: str
    thinking: str
    resolution: str
    beliefs: bool
    close_only: bool

    @property
    def label(self) -> str:
        beliefs = "with beliefs" if self.beliefs else "no beliefs"
        return f"{self.model}, thinking {self.thinking}, res {self.resolution}, {beliefs}"


def gemini_plan(full: bool) -> list[GeminiConfig]:
    """The Gemini runs, most important first, so a quota cut still leaves the main results.

    The default plan runs each comparison once, on the model where it matters (92 calls on 17
    frames): every model at the default settings, beliefs on and the thinking and resolution
    checks on 3.6 Flash, and minimal thinking on Flash-Lite. `full` runs every comparison on
    every model (142 calls).
    """
    flash, lite = "gemini-3.6-flash", "gemini-3.5-flash-lite"
    if not full:
        return [
            GeminiConfig(flash, "low", "high", beliefs=False, close_only=False),
            GeminiConfig(flash, "low", "high", beliefs=True, close_only=False),
            GeminiConfig(lite, "low", "high", beliefs=False, close_only=False),
            GeminiConfig("gemini-4-hydrogen", "low", "high", beliefs=False, close_only=False),
            GeminiConfig(flash, "minimal", "high", beliefs=False, close_only=True),
            GeminiConfig(flash, "low", "medium", beliefs=False, close_only=True),
            GeminiConfig(lite, "minimal", "high", beliefs=False, close_only=True),
        ]
    configs = []
    for model in GEMINI_MODELS:
        configs += [
            GeminiConfig(model, "low", "high", beliefs=False, close_only=False),
            GeminiConfig(model, "low", "high", beliefs=True, close_only=False),
            GeminiConfig(model, "low", "medium", beliefs=False, close_only=True),
        ]
        if model not in NO_MINIMAL_THINKING:
            configs.append(GeminiConfig(model, "minimal", "high", False, close_only=True))
    return configs


GIVE_UP_AFTER = 3  # frames in a row that fail on one model before its other frames are skipped
FAILED_IN_A_ROW: dict[str, int] = {}


@dataclass(frozen=True)
class GeminiResult:
    frame: Frame
    seen: Seen | None
    latency_s: float | None
    error: str | None
    thought_tokens: int | None


async def run_gemini(
    client: genai.Client,
    frame: Frame,
    config: GeminiConfig,
    prompt: str,
    schema: dict[str, Any],
    gate: asyncio.Semaphore,
) -> GeminiResult:
    key = {
        "model": config.model,
        "thinking": config.thinking,
        "resolution": config.resolution,
        "prompt": prompt,
        "schema": schema,
        "image": frame.sha,
    }

    async def call() -> Any:
        async with asyncio.timeout(GEMINI_TIMEOUT_S):  # a hard stop, whatever the SDK does
            interaction = await create()
        if interaction.status != "completed":
            raise RuntimeError(f"status {interaction.status}")
        usage = interaction.usage
        return {
            "output_text": interaction.output_text,
            "thought_tokens": usage.total_thought_tokens if usage else None,
        }

    async def create() -> Any:
        return await client.aio.interactions.create(
            model=config.model,
            input=[
                {"type": "text", "text": prompt},
                {
                    "type": "image",
                    "data": frame.b64,
                    "mime_type": "image/jpeg",
                    "resolution": config.resolution,
                },
            ],
            response_format={"type": "text", "mime_type": "application/json", "schema": schema},
            generation_config={"thinking_level": config.thinking},
            store=False,
            timeout=GEMINI_TIMEOUT_S,
        )

    async with gate:
        if FAILED_IN_A_ROW.get(config.model, 0) >= GIVE_UP_AFTER and not (
            cache_path("gemini", key).exists()
        ):
            skipped = f"skipped after {GIVE_UP_AFTER} failures in a row on {config.model}"
            return GeminiResult(frame, None, None, skipped, None)
        out = await cached("gemini", key, call)
    failed = out.response is None
    FAILED_IN_A_ROW[config.model] = FAILED_IN_A_ROW.get(config.model, 0) + 1 if failed else 0
    if out.response is None:
        return GeminiResult(frame, None, None, out.error, None)
    try:
        seen = Seen.model_validate_json(out.response["output_text"])
    except ValueError as exc:
        return GeminiResult(frame, None, out.latency_s, f"bad JSON: {exc}"[:200], None)
    return GeminiResult(frame, seen, out.latency_s, None, out.response["thought_tokens"])


def stored_items(seen: Seen, context: PerceptionContext) -> dict[str, SeenItem]:
    """What the worker would pass to `log_sighting`: drop rules 2 to 5 of the perception rules."""
    no_capture = set(context.rooms) - {lm.room for lm in context.landmarks}
    if seen.room in no_capture or seen.room == "unknown" or seen.room_confidence < ROOM_CUT:
        return {}
    kept: dict[str, SeenItem] = {}
    for item in seen.items:
        if item.landmark == "none" and not item.in_hand:
            continue
        if item.confidence < ITEM_CUT:
            continue
        if item.item not in kept or item.confidence > kept[item.item].confidence:
            kept[item.item] = item
    return kept


# --------------------------------------------------------------------------------------------
# Scoring and tables
# --------------------------------------------------------------------------------------------


def _count(frames: Iterable[Frame], distance: str) -> int:
    return sum(1 for f in frames if f.truth.distance == distance)


def _ms(values: list[float]) -> str:
    return f"{statistics.median(values) * 1000:.0f}" if values else "-"


def _s(values: list[float], worst: bool = False) -> str:
    if not values:
        return "-"
    return f"{(max(values) if worst else statistics.median(values)):.1f}"


def cp2(frames: list[Frame], hit: set[str], false_alarms: int) -> str:
    """CP2: each item found in at least 8 of 10 of its close-ups, at most 1 false alarm."""
    missing = []
    for item in sorted({f.truth.item for f in frames if f.truth.distance == "close"}):
        mine = [f for f in frames if f.truth.distance == "close" and f.truth.item == item]
        found = sum(1 for f in mine if f.name in hit)
        if found < math.ceil(0.8 * len(mine)):
            missing.append(f"{item} {found}/{len(mine)}")
    if false_alarms > 1:
        missing.append(f"{false_alarms} false alarms")
    return "pass" if not missing else "fail: " + ", ".join(missing)


def detector_rows(results: list[DetectorResult], thresholds: Iterable[float]) -> list[list[str]]:
    frames = [r.frame for r in results]
    errors = sum(1 for r in results if r.detections is None)
    latencies = [r.latency_s for r in results if r.latency_s is not None]
    rows = []
    for t in thresholds:
        hits: set[str] = set()
        false_alarms = extras = 0
        for r in results:
            dets = [d for d in (r.detections or []) if d.confidence >= t]
            f = r.frame
            if f.truth.item is None:
                false_alarms += bool(dets)
                continue
            good = [d for d in dets if d.item == f.truth.item and iou(d.box, f.box) >= IOU_HIT]
            if good:
                hits.add(f.name)
            extras += any(d not in good for d in dets)
        close = sum(1 for f in frames if f.name in hits and f.truth.distance == "close")
        medium = sum(1 for f in frames if f.name in hits and f.truth.distance == "medium")
        missed = sorted(
            f.name for f in frames if f.truth.distance == "close" and f.name not in hits
        )
        rows.append(
            [
                f"{t:.2f}",
                f"{close}/{_count(frames, 'close')}",
                f"{medium}/{_count(frames, 'medium')}",
                f"{false_alarms}/{_count(frames, 'empty')}",
                str(extras),
                _ms(latencies),
                cp2(frames, hits, false_alarms),
                ", ".join(missed) or "-",
            ]
            + ([f"{errors} errors"] if errors else [])
        )
    return rows


def gemini_row(results: list[GeminiResult], context: PerceptionContext) -> list[str]:
    frames = [r.frame for r in results]
    hits: set[str] = set()
    placed: set[str] = set()
    boxed: set[str] = set()
    false_alarms = extras = room_ok = 0
    empty_lm_seen = empty_lm_total = 0
    notes: list[str] = []
    for r in results:
        f = r.frame
        if r.seen is None:
            notes.append(f"{f.name}: {r.error}")
            continue
        room_ok += r.seen.room == f.truth.room
        stored = stored_items(r.seen, context)
        address = f"{f.truth.room} > {f.truth.landmark}" if f.truth.landmark else None
        if f.truth.item is None:
            false_alarms += bool(stored)
            if stored:
                notes.append(f"{f.name}: false {', '.join(sorted(stored))}")
            if address:
                empty_lm_total += 1
                empty_lm_seen += address in r.seen.landmarks_in_view
            continue
        mine = stored.get(f.truth.item)
        if mine:
            hits.add(f.name)
            if mine.landmark == address:
                placed.add(f.name)
            else:
                notes.append(f"{f.name}: placed on {mine.landmark}")
        else:
            notes.append(f"{f.name}: missed")
        others = sorted(set(stored) - {f.truth.item})
        if others:
            extras += 1
            notes.append(f"{f.name}: extra {', '.join(others)}")
        raw = [i for i in r.seen.items if i.item == f.truth.item]
        if any((b := box_from_gemini(i.box_2d)) and iou(b, f.box) >= IOU_HIT for i in raw):
            boxed.add(f.name)

    def n(names: set[str], distance: str) -> str:
        got = sum(1 for f in frames if f.name in names and f.truth.distance == distance)
        return f"{got}/{_count(frames, distance)}"

    latencies = [r.latency_s for r in results if r.latency_s is not None]
    thoughts = [r.thought_tokens for r in results if r.thought_tokens is not None]
    has_medium, has_empty = _count(frames, "medium") > 0, _count(frames, "empty") > 0
    return [
        n(hits, "close"),
        n(placed, "close"),
        n(hits, "medium") if has_medium else "-",
        n(placed, "medium") if has_medium else "-",
        f"{false_alarms}/{_count(frames, 'empty')}" if has_empty else "-",
        str(extras),
        f"{room_ok}/{len(frames)}",
        f"{empty_lm_seen}/{empty_lm_total}" if has_empty else "-",
        n(boxed, "close"),
        n(boxed, "medium") if has_medium else "-",
        _s(latencies),
        _s(latencies, worst=True),
        f"{statistics.median(thoughts):.0f}" if thoughts else "-",
        cp2(frames, hits, false_alarms) if has_empty else "-",
        "; ".join(notes) or "-",
    ]


def table(header: list[str], rows: list[list[str]]) -> str:
    width = max(len(header), *(len(r) for r in rows)) if rows else len(header)
    header = header + [""] * (width - len(header))
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r + [""] * (width - len(r))) + " |" for r in rows]
    return "\n".join(out)


# --------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------


async def bake(only: set[str], concurrency: int, gemini_concurrency: int, full: bool) -> str:
    settings = get_settings()
    context = await db.perception_context()
    if {i.item for i in context.items} != set(WORDINGS["names"]):
        raise SystemExit("WORDINGS does not match the items in perception_context; update it")
    frames = load_frames(context)
    close = [f for f in frames if f.truth.distance == "close"]
    sections = [
        "# Bake-off",
        "",
        f"{len(close)} close-ups, {_count(frames, 'medium')} medium, "
        f"{_count(frames, 'empty')} empty. Frames sent at long side {MAX_SIDE} px, "
        f"JPEG {JPEG_QUALITY}. Box hit: IoU >= {IOU_HIT} against the hand-drawn box.",
    ]
    gate = asyncio.Semaphore(concurrency)

    async def gated(coro: Awaitable[Any]) -> Any:
        async with gate:
            return await coro

    if only & {"yolo", "sam3"}:
        if settings.roboflow_api_key is None:
            raise SystemExit("ROBOFLOW_API_KEY is not set")
        headers = {"Authorization": f"Bearer {settings.roboflow_api_key.get_secret_value()}"}
        async with httpx.AsyncClient(
            base_url=settings.roboflow_api_url, headers=headers, timeout=60
        ) as http:
            for family, runner, thresholds, title in (
                ("yolo", run_yolo, YOLO_THRESHOLDS, f"YOLO-World {YOLO_VERSION}"),
                ("sam3", run_sam3, SAM3_THRESHOLDS, "SAM 3 text prompts"),
            ):
                if family not in only:
                    continue
                rows = []
                for wording_name, wording in WORDINGS.items():
                    results = await asyncio.gather(
                        *(gated(runner(http, f, wording)) for f in frames)
                    )
                    for row in detector_rows(results, thresholds):
                        rows.append([wording_name, *row])
                    print(f"{title}: {wording_name} done", file=sys.stderr)
                sections += [
                    "",
                    f"## {title}",
                    "",
                    "Wordings: "
                    + "; ".join(f"{k}: {', '.join(v.values())}" for k, v in WORDINGS.items()),
                    "",
                    table(
                        [
                            "wording",
                            "threshold",
                            "close",
                            "medium",
                            "false alarms",
                            "extras",
                            "median ms",
                            "CP2",
                            "close-ups missed",
                        ],
                        rows,
                    ),
                ]

    if "gemini" in only:
        if settings.google_api_key is None:
            raise SystemExit("GOOGLE_API_KEY is not set")
        # SDK retries off: by default it retries 408, 409, 429 and 5xx up to 4 times inside one
        # call, which hid rate-limit waits inside the measured latency.
        client = genai.Client(
            api_key=settings.google_api_key.get_secret_value(),
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
        )
        gemini_gate = asyncio.Semaphore(gemini_concurrency)
        schema = build_schema(context)
        beliefs = tempting_beliefs(context)
        rows = []
        for config in gemini_plan(full):
            prompt = build_prompt(context, beliefs if config.beliefs else None)
            subset = close if config.close_only else frames
            results = await asyncio.gather(
                *(run_gemini(client, f, config, prompt, schema, gemini_gate) for f in subset)
            )
            scope = "close-ups" if config.close_only else "all frames"
            rows.append([config.label, scope, *gemini_row(results, context)])
            print(f"Gemini: {config.label} done", file=sys.stderr)
        sections += [
            "",
            "## Gemini, perception schema, no detector",
            "",
            "Counts after the worker's drop rules (room cut "
            f"{ROOM_CUT}, item cut {ITEM_CUT}). Beliefs runs use: "
            + "; ".join(f"{b.item} on {b.address}" for b in beliefs)
            + ".",
            "",
            table(
                [
                    "run",
                    "frames",
                    "close hit",
                    "close placed",
                    "medium hit",
                    "medium placed",
                    "false alarms",
                    "extras",
                    "room ok",
                    "empty landmark in view",
                    "box close",
                    "box medium",
                    "median s",
                    "worst s",
                    "thought tokens",
                    "CP2",
                    "notes",
                ],
                rows,
            ),
        ]
    if RATE_LIMITED:
        sections.insert(
            3,
            f"\n{RATE_LIMITED} calls were refused with 429 and retried; latencies time only the "
            "attempt that succeeded.",
        )
    return "\n".join(sections) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", default="yolo,sam3,gemini", help="comma list: yolo,sam3,gemini")
    parser.add_argument("--concurrency", type=int, default=4, help="Roboflow calls in flight")
    parser.add_argument("--gemini-concurrency", type=int, default=1, help="Gemini calls in flight")
    parser.add_argument(
        "--full", action="store_true", help="every Gemini comparison on every model (142 calls)"
    )
    args = parser.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if not only <= {"yolo", "sam3", "gemini"}:
        parser.error("--only takes yolo, sam3 and gemini")
    report = asyncio.run(bake(only, args.concurrency, args.gemini_concurrency, args.full))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
