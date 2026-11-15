"""The bake-off's pure parts: file-name ground truth, boxes, the schema and the drop rules."""

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


def test_iou() -> None:
    box = (0.0, 0.0, 100.0, 100.0)
    assert bakeoff.iou(box, box) == 1.0
    assert bakeoff.iou(box, (200.0, 200.0, 300.0, 300.0)) == 0.0
    assert bakeoff.iou(box, (0.0, 50.0, 100.0, 150.0)) == pytest.approx(1 / 3)


def test_gemini_boxes_are_clamped_and_reordered() -> None:
    assert bakeoff.box_from_gemini([600, 900, 100, -5]) == (100.0, 0.0, 600.0, 900.0)
    assert bakeoff.box_from_gemini([1, 2, 3]) is None


def test_schema_is_deterministic_and_uses_addresses() -> None:
    reordered = CONTEXT.model_copy(
        update={"landmarks": CONTEXT.landmarks[::-1], "items": CONTEXT.items[::-1]}
    )
    schema = bakeoff.build_schema(CONTEXT)

    assert json.dumps(schema) == json.dumps(bakeoff.build_schema(reordered))
    item = schema["properties"]["items"]["items"]["properties"]
    assert item["landmark"]["enum"] == [
        "b_school_classroom > chair",
        "b_school_classroom > floor",
        "b_school_classroom > table",
        "none",
    ]
    assert schema["properties"]["room"]["enum"][-1] == "unknown"


def test_prompt_lists_beliefs_only_when_asked() -> None:
    beliefs = bakeoff.tempting_beliefs(CONTEXT)

    assert "last seen" not in bakeoff.build_prompt(CONTEXT, None)
    assert "- glasses: b_school_classroom > table, 12 minutes ago" in bakeoff.build_prompt(
        CONTEXT, beliefs
    )


def seen(room: str = "b_school_classroom", room_confidence: float = 0.9, **item: object):
    entry = {"item": "keys", "landmark": "b_school_classroom > table", "confidence": 0.8}
    return bakeoff.Seen.model_validate(
        {
            "room": room,
            "room_confidence": room_confidence,
            "landmarks_in_view": [],
            "items": [{**entry, **item}],
        }
    )


@pytest.mark.parametrize(
    ("perception", "kept"),
    [
        (seen(), True),
        (seen(room="bathroom"), False),  # no-capture room
        (seen(room="unknown"), False),
        (seen(room_confidence=0.5), False),  # below the room cut
        (seen(confidence=0.4), False),  # below the item cut
        (seen(landmark="none"), False),  # somewhere else, not in hand
        (seen(landmark="none", in_hand=True), True),
    ],
)
def test_stored_items_applies_the_worker_drop_rules(perception: bakeoff.Seen, kept: bool) -> None:
    assert bool(bakeoff.stored_items(perception, CONTEXT)) is kept


def test_stored_items_keeps_the_most_confident_duplicate() -> None:
    perception = seen()
    twice = perception.model_copy(
        update={
            "items": [
                *perception.items,
                bakeoff.SeenItem(
                    item="keys", landmark="b_school_classroom > floor", confidence=0.9
                ),
            ]
        }
    )

    assert bakeoff.stored_items(twice, CONTEXT)["keys"].landmark == "b_school_classroom > floor"
