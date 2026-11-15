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

from app.config import get_settings
from app.memory import db
from app.memory.schema import Belief, PerceptionContext
from app.perception.detector import parse_response
from app.perception.frame import JPEG_QUALITY, MAX_SIDE, load_frame
from app.perception.perceive import apply_drop_rules
from app.perception.schema import (
    Box,
    Detection,
    ItemSeen,
    Perception,
    box_from_pixels,
    build_json_schema,
    iou,
)
from app.perception.vlm import build_input, build_prompt

ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = ROOT / "tests" / "fixtures" / "frames"
CACHE_DIR = ROOT / ".cache" / "bakeoff"

IOU_HIT = 0.5

YOLO_VERSION = "v2-l"
YOLO_FLOOR = 0.05
YOLO_THRESHOLDS = (0.05, 0.1, 0.2, 0.3)
SAM3_FLOOR = 0.1
SAM3_THRESHOLDS = (0.3, 0.5, 0.7)

GEMINI_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-4-hydrogen")
NO_MINIMAL_THINKING = {"gemini-4-hydrogen"}  # thinking doc: minimal is not supported on Gemini 4
GEMINI_TIMEOUT_S = 60.0  # generous on purpose: the bake-off measures latency, it does not cut it

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


def load_frames(context: PerceptionContext) -> list[Frame]:
    boxes = json.loads((FRAMES_DIR / "boxes.json").read_text())
    frames = []
    paths = sorted(p for p in FRAMES_DIR.iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    for path in paths:
        truth = parse_name(path.stem, context)
        box = boxes.get(path.stem)
        if (box is None) != (truth.item is None):
            raise ValueError(f"{path.name}: boxes.json must have a box for item frames only")
        # Upright, at most MAX_SIDE, no metadata; the committed fixtures pass byte for byte.
        image = load_frame(path.read_bytes())
        frames.append(
            Frame(
                path.stem, truth, tuple(box) if box else None, image.jpeg, image.width, image.height
            )
        )
    if not frames:
        raise SystemExit(f"no frames in {FRAMES_DIR}")
    return frames


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
        item = by_class[p["class"]]
        detections.append(
            Detection(item=item, prompt=wording[item], confidence=p["confidence"], box=box)
        )
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
    detections = parse_response(out.response, frame.width, frame.height, wording)
    return DetectorResult(frame, detections, out.latency_s, None)


# --------------------------------------------------------------------------------------------
# Gemini: the schema, prompt and drop rules are app.perception's, so this measures what runs
# --------------------------------------------------------------------------------------------


def tempting_beliefs(context: PerceptionContext) -> list[Belief]:
    address = {lm.landmark: lm.address for lm in context.landmarks}
    return [
        Belief(item=item, address=address[lm], status="active", minutes_ago=minutes)
        for item, (lm, minutes) in TEST_BELIEFS.items()
        if lm in address and item in {i.item for i in context.items}
    ]


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
    seen: Perception | None
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
            input=build_input(frame.jpeg, prompt, config.resolution),
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
        seen = Perception.model_validate_json(out.response["output_text"])
    except ValueError as exc:
        return GeminiResult(frame, None, out.latency_s, f"bad JSON: {exc}"[:200], None)
    return GeminiResult(frame, seen, out.latency_s, None, out.response["thought_tokens"])


def stored_items(seen: Perception, context: PerceptionContext) -> dict[str, ItemSeen]:
    """What the worker would pass to `log_sighting`: the drop rules at the configured cuts."""
    settings = get_settings()
    verdict = apply_drop_rules(
        seen, context, room_cut=settings.room_cut, item_cut=settings.item_cut
    )
    return {item.item: item for item in verdict.kept}


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
        if any(i.box and iou(i.box, f.box) >= IOU_HIT for i in raw):
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
        schema = build_json_schema(context)
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
            f"{settings.room_cut}, item cut {settings.item_cut}). Beliefs runs use: "
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
