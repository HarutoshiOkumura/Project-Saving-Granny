"""Blur and duplicate filters on fixture frames, and their per-device exceptions."""

import io
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image, ImageFilter

from app.perception.filters import FrameGate, sharpness, similarity, thumbnail
from app.perception.frame import Frame, load_frame
from tests.perception_fakes import FRAMES

T0 = datetime(2026, 11, 15, 1, 0, tzinfo=UTC)


def fixture(name: str) -> Frame:
    return load_frame((FRAMES / f"{name}.jpg").read_bytes())


def blurred(frame: Frame, radius: float) -> Frame:
    with Image.open(io.BytesIO(frame.jpeg)) as image:
        soft = image.filter(ImageFilter.GaussianBlur(radius))
    buffer = io.BytesIO()
    soft.save(buffer, "JPEG", quality=90)
    return load_frame(buffer.getvalue())


def gate() -> FrameGate:
    return FrameGate(blur_cut=25.0, duplicate_cut=0.95, refresh_s=10.0)


def test_every_fixture_frame_is_sharp_enough() -> None:
    for path in FRAMES.glob("*.jpg"):
        assert sharpness(load_frame(path.read_bytes())) > 500, path.stem


def test_a_smeared_frame_scores_far_lower() -> None:
    frame = fixture("close_glasses_table_01")

    assert sharpness(blurred(frame, 8)) < 25 < sharpness(frame)


def test_identical_frames_are_fully_similar_and_different_ones_are_not() -> None:
    table, chair = thumbnail(fixture("empty_table_01")), thumbnail(fixture("empty_chair_01"))

    assert similarity(table, table) == pytest.approx(1.0)
    assert similarity(table, chair) < 0.5


def test_frames_of_different_shape_are_never_similar() -> None:
    portrait = thumbnail(fixture("empty_table_01"))

    assert similarity(portrait, portrait.T.copy()) == 0.0


def test_gate_drops_a_blurry_frame_and_does_not_remember_it() -> None:
    g = gate()

    verdict = g.check(blurred(fixture("empty_table_01"), 8), T0)

    assert verdict.result == "blurry"
    assert g.last_thumb is None


def test_gate_drops_a_duplicate_of_the_last_accepted_frame() -> None:
    g, frame = gate(), fixture("empty_table_01")

    assert g.check(frame, T0).result == "ok"
    second = g.check(frame, T0 + timedelta(seconds=2))

    assert second.result == "duplicate"
    assert second.similarity == pytest.approx(1.0)


def test_gate_keeps_one_duplicate_as_the_second_look_after_a_sighting() -> None:
    g, frame = gate(), fixture("close_keys_table_01")
    g.check(frame, T0)
    g.second_look_due = True  # the worker sets this when the frame logged a sighting

    assert g.check(frame, T0 + timedelta(seconds=1)).result == "ok"
    assert g.check(frame, T0 + timedelta(seconds=2)).result == "duplicate"


def test_gate_keeps_a_duplicate_once_the_last_accepted_frame_is_stale() -> None:
    g, frame = gate(), fixture("empty_chair_01")
    g.check(frame, T0)

    assert g.check(frame, T0 + timedelta(seconds=9)).result == "duplicate"
    assert g.check(frame, T0 + timedelta(seconds=10)).result == "ok"
    assert g.check(frame, T0 + timedelta(seconds=12)).result == "duplicate"


def test_a_new_view_is_accepted_and_becomes_the_reference() -> None:
    g = gate()
    g.check(fixture("empty_table_01"), T0)

    assert g.check(fixture("empty_chair_01"), T0 + timedelta(seconds=1)).result == "ok"
    assert g.check(fixture("empty_chair_01"), T0 + timedelta(seconds=2)).result == "duplicate"
