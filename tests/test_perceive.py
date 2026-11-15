"""perceive(): the SAM 3 gate, crop boxes, and the drop rules, with faked model calls."""

import asyncio
from typing import Any

import pytest

from app.perception import detector, perceive, vlm
from app.perception.frame import Frame
from app.perception.perceive import Verdict, apply_drop_rules, with_crop_boxes
from app.perception.schema import Detection, ItemSeen, Perception
from tests.perception_fakes import CHAIR, CONTEXT, FLOOR, ROOM, TABLE, gemini_answer

FRAME = Frame(b"\xff\xd8fake", width=1440, height=1920)
KEYS_BOX = (470.0, 347.0, 650.0, 627.0)  # Gemini's box in gemini_answer()


def sam(item: str, confidence: float, box: tuple[float, float, float, float]) -> Detection:
    return Detection(item=item, prompt=detector.PROMPTS[item], confidence=confidence, box=box)


class Fakes:
    def __init__(self) -> None:
        self.detections: list[Detection] | Exception = []
        self.answer: str | None = gemini_answer()
        self.looks = 0


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> Fakes:
    state = Fakes()

    async def fake_detect(frame: Frame) -> list[Detection]:
        if isinstance(state.detections, Exception):
            raise state.detections
        return state.detections

    async def fake_look(jpeg: bytes, context: Any) -> Perception | None:
        state.looks += 1
        return None if state.answer is None else Perception.model_validate_json(state.answer)

    monkeypatch.setattr(detector, "detect", fake_detect)
    monkeypatch.setattr(vlm, "look", fake_look)
    return state


def run(empty_look: bool = False) -> perceive.PerceiveResult:
    return asyncio.run(perceive.perceive(FRAME, CONTEXT, empty_look=empty_look))


# --------------------------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------------------------


def test_a_demo_item_at_the_gate_opens_it(fakes: Fakes) -> None:
    fakes.detections = [sam("keys", 0.5, KEYS_BOX)]

    result = run()

    assert result.gate == "open"
    assert fakes.looks == 1
    assert result.perception is not None and result.perception.items[0].item == "keys"
    assert result.vlm_ms is not None and result.error is None


def test_below_the_gate_gemini_is_not_asked(fakes: Fakes) -> None:
    fakes.detections = [sam("watch", 0.49, KEYS_BOX)]

    result = run()

    assert result.gate == "closed"
    assert result.perception is None
    assert result.vlm_ms is None
    assert result.detections == fakes.detections
    assert fakes.looks == 0


def test_an_empty_look_asks_gemini_with_the_gate_closed(fakes: Fakes) -> None:
    fakes.answer = gemini_answer([], landmarks_in_view=[TABLE, CHAIR])

    result = run(empty_look=True)

    assert result.gate == "empty_look"
    assert result.perception is not None
    assert result.perception.landmarks_in_view == [TABLE, CHAIR]
    assert fakes.looks == 1


def test_an_empty_look_is_just_open_when_sam3_saw_something(fakes: Fakes) -> None:
    fakes.detections = [sam("bag", 0.9, KEYS_BOX)]

    assert run(empty_look=True).gate == "open"


def test_a_failed_detector_fails_open(fakes: Fakes) -> None:
    fakes.detections = detector.DetectorError("ConnectError: down")

    result = run()

    assert result.gate == "detector_failed"
    assert result.error == "ConnectError: down"
    assert result.perception is not None
    assert result.perception.items[0].box_source == "gemini"


def test_an_item_sam3_cannot_look_for_fails_open(fakes: Fakes) -> None:
    wallet = CONTEXT.items[0].model_copy(update={"item": "wallet"})
    context = CONTEXT.model_copy(update={"items": [*CONTEXT.items, wallet]})

    result = asyncio.run(perceive.perceive(FRAME, context))

    assert result.gate == "no_prompt"
    assert fakes.looks == 1


def test_a_failed_gemini_call_gives_no_perception(fakes: Fakes) -> None:
    fakes.detections = [sam("keys", 0.9, KEYS_BOX)]
    fakes.answer = None

    result = run()

    assert result.gate == "open"
    assert result.perception is None
    assert result.vlm_ms is not None


# --------------------------------------------------------------------------------------------
# Crop boxes
# --------------------------------------------------------------------------------------------


def test_the_sam3_box_that_agrees_best_replaces_gemini_box(fakes: Fakes) -> None:
    tight = (480.0, 350.0, 640.0, 620.0)  # IoU about 0.86 with Gemini's box
    looser = (450.0, 300.0, 700.0, 700.0)  # IoU about 0.5
    fakes.detections = [sam("bag", 0.3, looser), sam("keys", 0.9, tight)]

    item = run().perception.items[0]

    assert item.box == tight
    assert item.box_source == "sam3"


def test_sam3_label_is_ignored_for_the_box(fakes: Fakes) -> None:
    """Step 04: SAM 3 called a distant watch "bunch of keys". Only the overlap counts."""
    fakes.answer = gemini_answer([{"item": "watch"}])
    fakes.detections = [sam("keys", 0.6, (480.0, 350.0, 640.0, 620.0))]

    item = run().perception.items[0]

    assert item.item == "watch"
    assert item.box_source == "sam3"


def test_gemini_box_stays_when_no_sam3_box_agrees(fakes: Fakes) -> None:
    fakes.detections = [sam("keys", 0.9, (0.0, 0.0, 100.0, 100.0))]

    item = run().perception.items[0]

    assert item.box == KEYS_BOX
    assert item.box_source == "gemini"


def test_an_item_without_a_box_keeps_none() -> None:
    perception = Perception.model_validate_json(gemini_answer([{"box_2d": [1, 1, 1, 1]}]))

    (item,) = with_crop_boxes(perception, [sam("keys", 0.9, KEYS_BOX)]).items

    assert item.box is None


# --------------------------------------------------------------------------------------------
# Drop rules
# --------------------------------------------------------------------------------------------


def perception(room: str = ROOM, room_confidence: float = 0.9, **item: Any) -> Perception:
    return Perception.model_validate_json(
        gemini_answer([item], room=room, room_confidence=room_confidence)
    )


def verdict(p: Perception) -> Verdict:
    return apply_drop_rules(p, CONTEXT, room_cut=0.6, item_cut=0.5)


def test_a_clear_item_is_kept() -> None:
    result = verdict(perception())

    assert result.frame == "keep"
    assert [i.item for i in result.kept] == ["keys"]
    assert result.dropped == []


def test_rule_1_a_no_capture_room_drops_the_frame() -> None:
    assert verdict(perception(room="bathroom")) == Verdict(frame="no_capture", kept=[], dropped=[])


def test_rule_1_comes_before_the_room_cut() -> None:
    assert verdict(perception(room="bathroom", room_confidence=0.1)).frame == "no_capture"


@pytest.mark.parametrize(("room", "confidence"), [("unknown", 0.9), (ROOM, 0.59)])
def test_rule_2_an_unsure_room_drops_the_frame(room: str, confidence: float) -> None:
    result = verdict(perception(room=room, room_confidence=confidence))

    assert result == Verdict(frame="room_unsure", kept=[], dropped=[])


def test_rule_2_the_room_cut_itself_passes() -> None:
    assert verdict(perception(room_confidence=0.6)).frame == "keep"


def test_rule_3_no_place_and_not_in_hand_drops_the_item() -> None:
    result = verdict(perception(landmark="none"))

    assert result.frame == "keep"
    assert result.kept == []
    assert [(d.item, d.reason) for d in result.dropped] == [("keys", "no_place")]


def test_rule_3_an_item_in_hand_needs_no_place() -> None:
    result = verdict(perception(landmark="none", in_hand=True))

    assert [(i.item, i.in_hand) for i in result.kept] == [("keys", True)]


def test_rule_4_below_the_item_cut_drops_the_item() -> None:
    result = verdict(perception(confidence=0.49))

    assert result.kept == []
    assert [(d.reason, d.confidence) for d in result.dropped] == [("low_confidence", 0.49)]


def test_rule_4_the_item_cut_itself_passes() -> None:
    assert len(verdict(perception(confidence=0.5)).kept) == 1


def test_rule_5_the_most_confident_duplicate_wins() -> None:
    twice = Perception.model_validate_json(
        gemini_answer(
            [
                {"landmark": TABLE, "confidence": 0.7},
                {"landmark": FLOOR, "confidence": 0.9},
                {"landmark": CHAIR, "confidence": 0.8},
            ]
        )
    )

    result = verdict(twice)

    assert [(i.item, i.landmark) for i in result.kept] == [("keys", FLOOR)]
    assert sorted(d.confidence for d in result.dropped) == [0.7, 0.8]
    assert {d.reason for d in result.dropped} == {"duplicate"}


def test_rule_5_a_tie_keeps_the_first_entry() -> None:
    twice = Perception.model_validate_json(
        gemini_answer([{"landmark": TABLE}, {"landmark": FLOOR}])
    )

    assert verdict(twice).kept[0].landmark == TABLE


def test_rule_5_runs_after_rules_3_and_4() -> None:
    """A confident entry with no place must not knock out a weaker one on a landmark."""
    entries = gemini_answer(
        [{"landmark": "none", "confidence": 0.95}, {"landmark": TABLE, "confidence": 0.6}]
    )

    result = verdict(Perception.model_validate_json(entries))

    assert [i.landmark for i in result.kept] == [TABLE]


def test_several_items_are_kept_in_answer_order() -> None:
    both = Perception.model_validate_json(
        gemini_answer([{"item": "watch"}, {"item": "keys", "landmark": CHAIR}])
    )

    kept = verdict(both).kept

    assert [(i.item, i.landmark) for i in kept] == [("watch", TABLE), ("keys", CHAIR)]
    assert all(isinstance(i, ItemSeen) for i in kept)
