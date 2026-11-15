"""The bake-off's own parts: file-name ground truth and frame loading. The schema, prompt,
boxes and drop rules it measures are app.perception's, tested in tests/test_perception.py."""

import json
from pathlib import Path

import pytest

from app.memory.schema import PerceptionContext
from scripts import bakeoff

FRAMES = Path(__file__).parent / "fixtures" / "frames"

CONTEXT = PerceptionContext.model_validate(
    {
        "rooms": ["bathroom", "b_school_classroom"],
        "landmarks": [
            {"room": "b_school_classroom", "landmark": "table", "kind": "surface"},
            {"room": "b_school_classroom", "landmark": "chair", "kind": "surface"},
            {"room": "b_school_classroom", "landmark": "floor", "kind": "floor"},
        ],
        "items": [
            {"item": "water bottle", "looks_like": "dark blue"},
            {"item": "glasses", "looks_like": "black"},
            {"item": "keys"},
            {"item": "bag"},
            {"item": "watch"},
        ],
        "beliefs": None,
    }
)


def test_every_fixture_frame_name_parses_and_item_frames_have_a_box() -> None:
    boxes = json.loads((FRAMES / "boxes.json").read_text())
    stems = sorted(p.stem for p in FRAMES.glob("*.jpg"))
    assert stems

    for stem in stems:
        truth = bakeoff.parse_name(stem, CONTEXT)
        assert (truth.item is None) == (stem not in boxes)


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        (
            "close_water-bottle_table_01",
            bakeoff.Truth("close", "water bottle", "table", "b_school_classroom"),
        ),
        ("medium_keys_floor_02", bakeoff.Truth("medium", "keys", "floor", "b_school_classroom")),
        ("empty_chair_01", bakeoff.Truth("empty", None, "chair", "b_school_classroom")),
        ("empty_b-school-classroom_01", bakeoff.Truth("empty", None, None, "b_school_classroom")),
    ],
)
def test_parse_name_maps_hyphens_back_to_seeded_names(stem: str, expected: bakeoff.Truth) -> None:
    assert bakeoff.parse_name(stem, CONTEXT) == expected


@pytest.mark.parametrize(
    "stem",
    ["close_blue_waterbottle_chair", "close_wallet_table_01", "far_keys_table_01", "empty_sofa_01"],
)
def test_parse_name_rejects_names_off_the_pattern(stem: str) -> None:
    with pytest.raises(ValueError):
        bakeoff.parse_name(stem, CONTEXT)


def test_load_frames_keeps_committed_fixtures_byte_for_byte() -> None:
    """The bake-off's cache keys are hashes of these bytes."""
    frames = bakeoff.load_frames(CONTEXT)

    assert len(frames) == len(list(FRAMES.glob("*.jpg")))
    for frame in frames:
        assert frame.jpeg == (FRAMES / f"{frame.name}.jpg").read_bytes()


def test_tempting_beliefs_reach_the_prompt_only_when_passed() -> None:
    beliefs = bakeoff.tempting_beliefs(CONTEXT)

    assert "last seen" not in bakeoff.build_prompt(CONTEXT, None)
    assert "- glasses: b_school_classroom > table, 12 minutes ago" in bakeoff.build_prompt(
        CONTEXT, beliefs
    )


def test_stored_items_uses_the_shared_drop_rules() -> None:
    perception = bakeoff.Perception.model_validate(
        {
            "room": "b_school_classroom",
            "room_confidence": 0.9,
            "landmarks_in_view": [],
            "items": [
                {"item": "keys", "landmark": "b_school_classroom > table", "confidence": 0.8},
                {"item": "watch", "landmark": "none", "confidence": 0.9},
            ],
        }
    )

    assert list(bakeoff.stored_items(perception, CONTEXT)) == ["keys"]
