"""Every fixture frame through perceive(), the drop rules and crop(), with the real SAM 3 and
Gemini answers recorded by the live test (`tests/fixtures/responses/`). No network.

This pins what the live run measured on 15 Nov: 17/17 frames fully correct, every crop box from
SAM 3. Re-record with `RUN_LIVE=1 LIVE_FRAMES=all RECORD=1 uv run pytest -m live -s`.
"""

import asyncio
import io
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from app.perception import detector, vlm
from app.perception.frame import crop, crop_pixels, load_frame
from app.perception.perceive import PerceiveResult, apply_drop_rules, perceive
from app.perception.schema import iou
from scripts.bakeoff import parse_name
from tests.perception_fakes import CONTEXT, FRAMES, RESPONSES

RECORDINGS = sorted(RESPONSES.glob("*.json"))
BOXES = json.loads((FRAMES / "boxes.json").read_text())


def replay(
    monkeypatch: pytest.MonkeyPatch, path: Path, empty_look: bool
) -> tuple[PerceiveResult, list[dict[str, Any]]]:
    recording = json.loads(path.read_text())
    requests: list[dict[str, Any]] = []

    async def recorded_sam3(body: dict[str, Any], settings: Any) -> Any:
        return recording["sam3"]

    async def recorded_gemini(request: dict[str, Any], settings: Any) -> str:
        requests.append(request)
        return json.dumps(recording["gemini"])

    monkeypatch.setattr(detector, "_post", recorded_sam3)
    monkeypatch.setattr(vlm, "_ask", recorded_gemini)
    frame = load_frame((FRAMES / f"{path.stem}.jpg").read_bytes())
    return asyncio.run(perceive(frame, CONTEXT, empty_look=empty_look)), requests


def test_every_fixture_frame_has_a_recording() -> None:
    assert [p.stem for p in RECORDINGS] == sorted(p.stem for p in FRAMES.glob("*.jpg"))


@pytest.mark.parametrize("path", RECORDINGS, ids=lambda p: p.stem)
def test_recorded_frame_is_placed_correctly(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    truth = parse_name(path.stem, CONTEXT)
    result, requests = replay(monkeypatch, path, empty_look=truth.item is None)

    assert result.perception is not None
    assert requests[0]["store"] is False
    verdict = apply_drop_rules(result.perception, CONTEXT, room_cut=0.6, item_cut=0.5)
    assert verdict.frame == "keep"
    assert result.perception.room == truth.room
    address = f"{truth.room} > {truth.landmark}" if truth.landmark else None

    if truth.item is None:
        assert verdict.kept == []
        assert address is None or address in result.perception.landmarks_in_view
        return

    assert result.gate == "open"
    (kept,) = verdict.kept
    assert (kept.item, kept.landmark, kept.in_hand) == (truth.item, address, False)
    assert kept.box is not None and kept.box_source == "sam3"
    hand_box = tuple(BOXES[path.stem])
    assert iou(kept.box, hand_box) >= 0.5

    frame = load_frame((FRAMES / f"{path.stem}.jpg").read_bytes())
    left, top, right, bottom = crop_pixels(frame, kept.box)
    assert left <= hand_box[1] / 1000 * frame.width + 2
    assert right >= hand_box[3] / 1000 * frame.width - 2
    assert top <= hand_box[0] / 1000 * frame.height + 2
    assert bottom >= hand_box[2] / 1000 * frame.height - 2
    assert (right - left) * (bottom - top) < frame.width * frame.height  # never the full frame
    with Image.open(io.BytesIO(crop(frame, kept.box))) as image:
        assert image.format == "JPEG"


@pytest.mark.parametrize(
    "path", [p for p in RECORDINGS if p.stem.startswith("empty_")], ids=lambda p: p.stem
)
def test_the_gate_spares_gemini_on_empty_frames(
    monkeypatch: pytest.MonkeyPatch, path: Path
) -> None:
    """Without an empty look, Gemini is asked only where SAM 3 scored a demo item at 0.5 or more:
    on these frames only the bare carpet (a "wristwatch" at 0.55), where Gemini then saw nothing."""
    result, requests = replay(monkeypatch, path, empty_look=False)

    if path.stem == "empty_floor_01":
        assert result.gate == "open"
        assert result.perception is not None and result.perception.items == []
    else:
        assert result.gate == "closed"
        assert result.perception is None
        assert requests == []
