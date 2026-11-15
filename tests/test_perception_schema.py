"""The response schema, the prompt, parsing Gemini's answer, and boxes. Pure functions only."""

import json

import pytest
from pydantic import ValidationError

from app.perception.schema import (
    ItemSeen,
    Perception,
    box_from_gemini,
    box_from_pixels,
    build_json_schema,
    iou,
)
from app.perception.vlm import build_input, build_prompt, within_context
from tests.perception_fakes import CHAIR, CONTEXT, FLOOR, ROOM, TABLE, gemini_answer


def test_schema_is_deterministic_whatever_the_context_order() -> None:
    shuffled = CONTEXT.model_copy(
        update={
            "rooms": CONTEXT.rooms[::-1],
            "landmarks": CONTEXT.landmarks[::-1],
            "items": CONTEXT.items[::-1],
        }
    )

    assert json.dumps(build_json_schema(CONTEXT)) == json.dumps(build_json_schema(shuffled))


def test_schema_never_carries_beliefs() -> None:
    no_beliefs = CONTEXT.model_copy(update={"beliefs": []})

    assert build_json_schema(CONTEXT) == build_json_schema(no_beliefs)
    assert "minutes" not in json.dumps(build_json_schema(CONTEXT))


def test_schema_enums_are_sorted_names_from_the_context() -> None:
    schema = build_json_schema(CONTEXT)
    top = schema["properties"]
    item = top["items"]["items"]["properties"]

    # Every room, the no-capture bathroom included (the worker drops it), then "unknown".
    assert top["room"]["enum"] == [ROOM, "bathroom", "unknown"]
    # Landmarks are addresses, so a landmark also fixes its room.
    assert top["landmarks_in_view"]["items"]["enum"] == [CHAIR, FLOOR, TABLE]
    assert item["landmark"]["enum"] == [CHAIR, FLOOR, TABLE, "none"]
    assert item["item"]["enum"] == ["bag", "glasses", "keys", "watch", "water bottle"]
    assert item["relation"]["enum"] == ["in", "next_to", "on", "under", "unknown"]


def test_schema_uses_only_keywords_gemini_enforces() -> None:
    schema = build_json_schema(CONTEXT)
    item = schema["properties"]["items"]["items"]

    assert schema["additionalProperties"] is False
    assert item["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert set(item["required"]) == set(item["properties"])
    assert schema["properties"]["room_confidence"] == {"type": "number", "minimum": 0, "maximum": 1}
    assert item["properties"]["box_2d"]["minItems"] == item["properties"]["box_2d"]["maxItems"] == 4
    for ignored in ("minLength", "maxLength", "uniqueItems"):
        assert ignored not in json.dumps(schema)


def test_prompt_lists_places_and_belongings_but_no_beliefs() -> None:
    prompt = build_prompt(CONTEXT)

    assert f"- {TABLE}\n" in prompt
    assert "- keys: black, car key fob with a few keys on a ring" in prompt
    assert "Never describe people." in prompt
    assert "in the wearer's own hand" in prompt
    assert "last seen" not in prompt  # D3: beliefs stay out
    assert "12 minutes" not in prompt


def test_prompt_lists_beliefs_only_when_passed() -> None:
    prompt = build_prompt(CONTEXT, CONTEXT.beliefs)

    assert f"- glasses: {TABLE}, 12 minutes ago" in prompt


def test_input_puts_the_text_before_the_image() -> None:
    text, image = build_input(b"\xff\xd8jpeg", "look")

    assert text == {"type": "text", "text": "look"}
    assert image == {
        "type": "image",
        "data": "/9hqcGVn",
        "mime_type": "image/jpeg",
        "resolution": "high",
    }


def test_perception_parses_gemini_answer() -> None:
    perception = Perception.model_validate_json(gemini_answer())

    assert perception.room == ROOM
    assert perception.landmarks_in_view == [TABLE]
    (keys,) = perception.items
    assert keys == ItemSeen(
        item="keys",
        landmark=TABLE,
        relation="on",
        in_hand=False,
        confidence=0.9,
        note="black key fob",
        box=(470.0, 347.0, 650.0, 627.0),
        box_source="gemini",
    )


def test_perception_clamps_confidences() -> None:
    perception = Perception.model_validate_json(
        gemini_answer([{"confidence": 1.7}], room_confidence=-0.2)
    )

    assert perception.room_confidence == 0.0
    assert perception.items[0].confidence == 1.0


@pytest.mark.parametrize(
    ("raw", "box"),
    [
        ([600, 900, 100, -5], (100.0, 0.0, 600.0, 900.0)),  # swapped corners, clamped
        ([0, 0, 1000, 1000], (0.0, 0.0, 1000.0, 1000.0)),
        ([500, 500, 500, 600], None),  # no area
        ([1, 2, 3], None),
        ("box", None),
        ([1, "a", 3, 4], None),
    ],
)
def test_box_from_gemini(raw: object, box: object) -> None:
    assert box_from_gemini(raw) == box


def test_an_item_with_a_useless_box_keeps_no_box() -> None:
    perception = Perception.model_validate_json(gemini_answer([{"box_2d": [5, 5, 5, 5]}]))

    assert perception.items[0].box is None
    assert perception.items[0].box_source is None


def test_unknown_relation_becomes_unknown_and_extra_keys_are_ignored() -> None:
    perception = Perception.model_validate_json(
        gemini_answer([{"relation": "beside", "colour": "black"}])
    )

    assert perception.items[0].relation == "unknown"


def test_perception_without_a_room_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Perception.model_validate_json('{"room_confidence": 0.9, "items": []}')


def test_within_context_replaces_names_off_the_lists() -> None:
    perception = Perception.model_validate_json(
        gemini_answer(
            [{"item": "wallet"}, {"item": "watch", "landmark": "kitchen > counter"}],
            room="kitchen",
            landmarks_in_view=[TABLE, "kitchen > counter"],
        )
    )

    checked = within_context(perception, CONTEXT)

    assert checked.room == "unknown"
    assert checked.landmarks_in_view == [TABLE]
    assert [(i.item, i.landmark) for i in checked.items] == [("watch", "none")]


def test_iou() -> None:
    box = (0.0, 0.0, 100.0, 100.0)
    assert iou(box, box) == 1.0
    assert iou(box, (200.0, 200.0, 300.0, 300.0)) == 0.0
    assert iou(box, (0.0, 50.0, 100.0, 150.0)) == pytest.approx(1 / 3)
    assert iou((0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)) == 0.0


def test_box_from_pixels_normalizes_to_1000() -> None:
    assert box_from_pixels(144, 192, 720, 960, 1440, 1920) == (100.0, 100.0, 500.0, 500.0)
