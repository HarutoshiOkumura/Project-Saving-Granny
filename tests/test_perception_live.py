"""Opt-in: perceive() on fixture frames with the real SAM 3 and Gemini, and the real context.

    RUN_LIVE=1 uv run pytest -m live -s                      # 3 frames
    RUN_LIVE=1 LIVE_FRAMES=all uv run pytest -m live -s      # every fixture frame
    RUN_LIVE=1 LIVE_FRAMES=all RECORD=1 uv run pytest -m live -s   # also rewrite the recordings

Staged photos of our own objects only (CLAUDE.md hard rules): inference, nothing uploaded to a
Roboflow project, `store=False` on Gemini. Reads `.env`; costs one SAM 3 and one Gemini call per
frame, one at a time (the free tier refused 4 in flight in step 04).

Item frames go through perceive() as the worker will send them. Empty frames are sent as empty
looks, so Gemini is asked even when the gate stays shut; the gate is still reported. A frame is
correct when the room is right and exactly the right item is kept on the right landmark (none on
an empty frame, whose named landmark must be listed in view). The table is printed and saved to
`.cache/live/perception.md`, the crops to `.cache/live/crops/`. With RECORD=1 the raw answers go
to `tests/fixtures/responses/`, where `test_perceive_replay.py` replays them offline.
"""

import asyncio
import json
import os
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app import config
from app.config import Settings, get_settings
from app.memory import db
from app.memory.schema import PerceptionContext
from app.perception import detector, vlm
from app.perception.frame import crop, load_frame
from app.perception.perceive import PerceiveResult, apply_drop_rules, perceive
from app.perception.schema import iou
from scripts.bakeoff import Truth, parse_name
from tests.perception_fakes import FRAMES, RESPONSES

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="calls paid APIs: RUN_LIVE=1"),
]

DEFAULT_FRAMES = ("close_glasses_table_01", "medium_watch_table_01", "empty_table_01")
MIN_SHARE = 0.8
OUT = config.ENV_FILE.parent / ".cache" / "live"


@pytest.fixture
def real_settings(monkeypatch: pytest.MonkeyPatch) -> Any:
    """The real `.env` instead of the fakes in conftest, for this test only."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", config.ENV_FILE)
    for module in (db, vlm, detector):
        monkeypatch.setattr(module, "_client", None)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@dataclass
class Row:
    name: str
    truth: Truth
    result: PerceiveResult
    correct: bool
    kept: str
    box_iou: float | None
    box_source: str | None
    sam3_best: float


def score(
    name: str, truth: Truth, result: PerceiveResult, context: PerceptionContext, hand_box: Any
) -> Row:
    settings = get_settings()
    p = result.perception
    sam3_best = max((d.confidence for d in result.detections), default=0.0)
    if p is None:
        return Row(name, truth, result, False, "no answer", None, None, sam3_best)
    verdict = apply_drop_rules(p, context, room_cut=settings.room_cut, item_cut=settings.item_cut)
    kept = {i.item: i for i in verdict.kept}
    address = f"{truth.room} > {truth.landmark}" if truth.landmark else None
    room_ok = p.room == truth.room and verdict.frame == "keep"
    box_iou = box_source = None
    if truth.item is None:
        correct = room_ok and not kept and (address is None or address in p.landmarks_in_view)
    else:
        mine = kept.get(truth.item)
        correct = room_ok and mine is not None and set(kept) == {truth.item}
        correct = correct and mine.landmark == address
        if mine and mine.box:
            box_iou, box_source = iou(mine.box, tuple(hand_box)), mine.box_source
    described = ", ".join(f"{i.item} {i.landmark} {i.confidence:.2f}" for i in verdict.kept)
    return Row(name, truth, result, correct, described or "-", box_iou, box_source, sam3_best)


async def run_frames(names: list[str], record: bool) -> tuple[list[Row], PerceptionContext]:
    context = await db.perception_context()
    boxes = json.loads((FRAMES / "boxes.json").read_text())
    rows = []
    for name in names:
        truth = parse_name(name, context)
        frame = load_frame((FRAMES / f"{name}.jpg").read_bytes())
        raw: dict[str, Any] = {}
        with pytest.MonkeyPatch.context() as mp:
            if record:
                _capture(mp, raw)
            result = await perceive(frame, context, empty_look=truth.item is None)
        row = score(name, truth, result, context, boxes.get(name))
        rows.append(row)
        print(f"{name}: {'ok' if row.correct else 'WRONG'} gate={result.gate} kept={row.kept}")
        if result.perception:
            for item in result.perception.items:
                if item.box:
                    path = OUT / "crops" / f"{name}_{item.item.replace(' ', '-')}.jpg"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(crop(frame, item.box))
        if record:
            _save(name, raw)
    return rows, context


def _capture(mp: pytest.MonkeyPatch, raw: dict[str, Any]) -> None:
    post, ask = detector._post, vlm._ask

    async def recording_post(body: dict[str, Any], settings: Any) -> Any:
        raw["sam3"] = await post(body, settings)
        return raw["sam3"]

    async def recording_ask(request: dict[str, Any], settings: Any) -> str:
        text = await ask(request, settings)
        raw["gemini"] = json.loads(text)
        raw["model"] = request["model"]
        return text

    mp.setattr(detector, "_post", recording_post)
    mp.setattr(vlm, "_ask", recording_ask)


def _save(name: str, raw: dict[str, Any]) -> None:
    RESPONSES.mkdir(parents=True, exist_ok=True)
    recording = {
        "model": raw.get("model"),
        "recorded": datetime.now(UTC).strftime("%Y-%m-%d"),
        "gemini": raw.get("gemini"),
        "sam3": {"prompt_results": raw["sam3"]["prompt_results"]} if "sam3" in raw else None,
    }
    (RESPONSES / f"{name}.json").write_text(dump_recording(recording))


def dump_recording(recording: dict[str, Any]) -> str:
    """Gemini's answer indented to read; SAM 3's polygons on one line to keep the file small."""
    lines = [
        f"  {json.dumps(key)}: "
        + (
            json.dumps(value, indent=2).replace("\n", "\n  ")
            if key == "gemini"
            else json.dumps(value)
        )
        for key, value in recording.items()
    ]
    return "{\n" + ",\n".join(lines) + "\n}\n"


def report(rows: list[Row], settings: Settings) -> str:
    correct = sum(r.correct for r in rows)
    lines = [
        f"# perceive() live, {datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
        "",
        f"Model {settings.perception_model}; room cut {settings.room_cut}, item cut "
        f"{settings.item_cut}, SAM 3 gate {settings.sam3_gate}. Empty frames sent as empty looks.",
        "",
        f"**All correct (room, landmark, item): {correct}/{len(rows)} "
        f"= {correct / len(rows):.0%}**",
        "",
        "| frame | gate | SAM 3 best | room (conf) | kept | crop box IoU (from) | SAM 3 ms | "
        "Gemini ms | correct |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        p = r.result.perception
        room = f"{p.room} ({p.room_confidence:.2f})" if p else "-"
        box = f"{r.box_iou:.2f} ({r.box_source})" if r.box_iou is not None else "-"
        lines.append(
            f"| {r.name} | {r.result.gate} | {r.sam3_best:.2f} | {room} | {r.kept} | {box} | "
            f"{r.result.detector_ms} | {r.result.vlm_ms or '-'} | {'yes' if r.correct else 'NO'} |"
        )
    lines += ["", *margins(rows)]
    return "\n".join(lines) + "\n"


def margins(rows: list[Row]) -> list[str]:
    """How far the observed scores sit from each cut: the evidence for tuning them (D11)."""
    answered = [r for r in rows if r.result.perception]
    perceptions = [(r, r.result.perception) for r in answered if r.result.perception]
    room_conf = [p.room_confidence for _, p in perceptions]
    right, wrong = [], []
    for r, p in perceptions:
        for item in p.items:
            place = f"{r.truth.room} > {r.truth.landmark}"
            good = item.item == r.truth.item and item.landmark == place
            (right if good else wrong).append(item.confidence)
    item_frames = [r.sam3_best for r in rows if r.truth.item]
    empty_frames = [r.sam3_best for r in rows if not r.truth.item]
    gemini_ms = [r.result.vlm_ms for r in rows if r.result.vlm_ms]
    sam3_ms = [r.result.detector_ms for r in rows]

    def low(values: list[float]) -> str:
        return f"{min(values):.2f}" if values else "-"

    def high(values: list[float]) -> str:
        return f"{max(values):.2f}" if values else "-"

    return [
        f"- room_confidence: lowest {low(room_conf)} (room cut sits below it)",
        f"- right items: lowest confidence {low(right)}; wrong or stray items: highest "
        f"{high(wrong)} ({len(wrong)} entries before the drop rules)",
        f"- SAM 3 best score: lowest on an item frame {low(item_frames)}, highest on an empty "
        f"frame {high(empty_frames)}",
        f"- SAM 3 ms median {statistics.median(sam3_ms):.0f}, worst {max(sam3_ms)}; Gemini ms "
        f"median {statistics.median(gemini_ms) if gemini_ms else 0:.0f}, worst "
        f"{max(gemini_ms, default=0)}",
    ]


def test_perceive_on_fixture_frames(real_settings: Settings) -> None:
    if real_settings.google_api_key is None or real_settings.roboflow_api_key is None:
        pytest.fail("GOOGLE_API_KEY and ROBOFLOW_API_KEY must be set in .env")
    chosen = os.environ.get("LIVE_FRAMES", "")
    if chosen == "all":
        names = sorted(p.stem for p in FRAMES.glob("*.jpg"))
    else:
        names = [n for n in chosen.split(",") if n] or list(DEFAULT_FRAMES)

    rows, _ = asyncio.run(run_frames(names, record=os.environ.get("RECORD") == "1"))

    text = report(rows, real_settings)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "perception.md").write_text(text)
    print("\n" + text)
    share = sum(r.correct for r in rows) / len(rows)
    assert share >= MIN_SHARE, f"only {share:.0%} of frames fully correct; see the table"


def test_recordings_cover_every_fixture_frame() -> None:
    """Runs with the live test so a new fixture frame is noticed; RECORD=1 fixes it."""
    stems = {p.stem for p in FRAMES.glob("*.jpg")}
    recorded = {p.stem for p in Path(RESPONSES).glob("*.json")}

    assert stems <= recorded, f"not recorded: {sorted(stems - recorded)}"
