"""The moment photo and the FaceTime card picture, on fixture frames. No network."""

import io
import json

import pytest
from PIL import Image

from app.perception.frame import Frame, crop, load_frame
from app.perception.schema import Box
from app.photo import (
    CARD_BACKGROUND,
    MOMENT_ASPECT,
    MOMENT_MAX_AREA,
    MOMENT_MAX_BYTES,
    MOMENT_MAX_SIDE,
    card_photo,
    moment_photo,
    moment_window,
    read_box,
)
from tests.perception_fakes import FRAMES

BOXES: dict[str, list[float]] = json.loads((FRAMES / "boxes.json").read_text())
CARD = (1280, 720)
AREA = (100, 0, 1180, 590)  # what agent/card.mjs asks for: what FaceTime shows, above the band


def frame_and_box(name: str) -> tuple[Frame, Box]:
    ymin, xmin, ymax, xmax = BOXES[name]
    return load_frame((FRAMES / f"{name}.jpg").read_bytes()), (ymin, xmin, ymax, xmax)


def size_of(jpeg: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(jpeg)) as image:
        return image.size


MEDIUM = ["medium_watch_chair_01", "medium_bag_floor_01", "medium_keys_table_01"]
ALL = [name for name in BOXES if not name.startswith("_")]


@pytest.mark.parametrize("name", ALL)
def test_the_window_holds_the_item_and_stays_inside_the_frame(name: str) -> None:
    frame, (ymin, xmin, ymax, xmax) = frame_and_box(name)

    left, top, right, bottom = moment_window(frame, (ymin, xmin, ymax, xmax))

    assert 0 <= left < right <= frame.width
    assert 0 <= top < bottom <= frame.height
    assert left <= xmin / 1000 * frame.width and xmax / 1000 * frame.width <= right
    assert top <= ymin / 1000 * frame.height and ymax / 1000 * frame.height <= bottom


@pytest.mark.parametrize("name", MEDIUM)
def test_a_moment_shows_the_whole_width_of_the_frame_but_never_the_full_frame(name: str) -> None:
    frame, box = frame_and_box(name)

    left, top, right, bottom = moment_window(frame, box)
    width, height = right - left, bottom - top

    assert (left, right) == (0, frame.width)  # an upright phone frame: all of its width
    assert width / height == pytest.approx(MOMENT_ASPECT, rel=0.01)
    assert width * height <= MOMENT_MAX_AREA * frame.width * frame.height
    crop_w, crop_h = size_of(crop(frame, box))
    assert width > 3 * crop_w and height > 2 * crop_h  # it shows what is around the item


def test_a_sideways_frame_is_capped_at_half_its_area() -> None:
    wide = Frame(b"", 1920, 1080)

    left, top, right, bottom = moment_window(wide, (450.0, 450.0, 550.0, 550.0))
    width, height = right - left, bottom - top

    assert width / height == pytest.approx(MOMENT_ASPECT, rel=0.01)
    assert width * height == pytest.approx(MOMENT_MAX_AREA * 1920 * 1080, rel=0.01)
    assert width < 1920 and height < 1080


def test_an_item_that_fills_the_frame_is_still_whole_in_its_moment() -> None:
    frame, box = frame_and_box("close_bag_table_01")  # the bag is 79% of the frame's width

    left, top, right, bottom = moment_window(frame, box)

    assert left <= box[1] / 1000 * frame.width and box[3] / 1000 * frame.width <= right
    assert top <= box[0] / 1000 * frame.height and box[2] / 1000 * frame.height <= bottom


@pytest.mark.parametrize("name", ALL)
def test_the_photo_is_small_and_remembers_where_the_item_is(name: str) -> None:
    frame, box = frame_and_box(name)

    jpeg = moment_photo(frame, box)

    assert jpeg.startswith(b"\xff\xd8\xff") and len(jpeg) <= MOMENT_MAX_BYTES
    assert max(size_of(jpeg)) <= MOMENT_MAX_SIDE
    inside = read_box(jpeg)
    assert inside is not None
    # The box inside the photo points at the same pixels as the box inside the frame.
    left, top, right, bottom = moment_window(frame, box)
    centre_x = left + (inside[1] + inside[3]) / 2000 * (right - left)
    centre_y = top + (inside[0] + inside[2]) / 2000 * (bottom - top)
    assert centre_x == pytest.approx((box[1] + box[3]) / 2000 * frame.width, abs=3)
    assert centre_y == pytest.approx((box[0] + box[2]) / 2000 * frame.height, abs=3)


def test_the_photo_carries_no_other_metadata() -> None:
    frame, box = frame_and_box("medium_watch_chair_01")

    with Image.open(io.BytesIO(moment_photo(frame, box))) as image:
        assert not image.getexif()
        assert set(image.info) <= {"jfif", "jfif_version", "jfif_unit", "jfif_density", "comment"}


def test_read_box_is_none_for_other_pictures_and_bad_comments() -> None:
    frame, box = frame_and_box("medium_watch_chair_01")
    plain = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(plain, "JPEG", comment=b"saveit-box:1,2,x,4")

    assert read_box(crop(frame, box)) is None  # a tight crop has no box
    assert read_box(plain.getvalue()) is None
    assert read_box(b"not an image") is None


def inside_area(x: float, y: float) -> bool:
    return AREA[0] <= x <= AREA[2] and AREA[1] <= y <= AREA[3]


@pytest.mark.parametrize("name", MEDIUM)
def test_the_card_shows_the_whole_photo_and_says_where_to_ring_the_item(name: str) -> None:
    frame, box = frame_and_box(name)
    photo = moment_photo(frame, box)

    card = card_photo(photo, *CARD, AREA)

    assert size_of(card.jpeg) == CARD
    assert card.circle is not None
    x, y, radius = card.circle
    assert inside_area(x, y) and 54 <= radius <= 0.3 * (AREA[3] - AREA[1])
    # Nothing is cut: the photo is drawn at one scale, as large as the area allows.
    photo_w, photo_h = size_of(photo)
    scale = min((AREA[2] - AREA[0]) / photo_w, (AREA[3] - AREA[1]) / photo_h)
    drawn_w, drawn_h = photo_w * scale, photo_h * scale
    left = AREA[0] + ((AREA[2] - AREA[0]) - drawn_w) / 2
    inside = read_box(photo)
    assert inside is not None
    assert x == pytest.approx(left + (inside[1] + inside[3]) / 2000 * drawn_w, abs=2)
    assert y == pytest.approx(AREA[1] + (inside[0] + inside[2]) / 2000 * drawn_h, abs=2)
    with Image.open(io.BytesIO(card.jpeg)) as image:
        for outside in ((40, 300), (1240, 300), (640, 650)):  # beside the area, and the band
            assert image.getpixel(outside) == pytest.approx(CARD_BACKGROUND, abs=6)
        # The photo's own corners are on the card, not cut away.
        for corner in ((left + 6, 6), (left + drawn_w - 6, drawn_h - 6)):
            assert image.getpixel(tuple(round(v) for v in corner)) != pytest.approx(
                CARD_BACKGROUND, abs=6
            )


def test_an_item_near_the_frame_edge_is_ringed_where_it_is() -> None:
    frame, _ = frame_and_box("medium_watch_chair_01")
    corner: Box = (930.0, 20.0, 990.0, 90.0)  # bottom left of the frame

    card = card_photo(moment_photo(frame, corner), *CARD, AREA)

    assert card.circle is not None
    x, y, _ = card.circle
    assert inside_area(x, y) and x < 400 and y > 400  # still bottom left, and in view


def test_no_ring_when_the_item_fills_the_picture() -> None:
    frame, box = frame_and_box("close_glasses_table_01")

    card = card_photo(moment_photo(frame, box), *CARD, AREA)

    assert size_of(card.jpeg) == CARD and card.circle is None


def test_no_ring_when_the_item_takes_up_nearly_half_the_picture() -> None:
    frame, _ = frame_and_box("medium_watch_chair_01")
    half: Box = (300.0, 500.0, 500.0, 950.0)  # 45% of the frame's width: a ring would frame it

    card = card_photo(moment_photo(frame, half), *CARD, AREA)

    assert card.circle is None


def test_a_tight_crop_is_shown_whole_on_the_dark_card_without_a_ring() -> None:
    frame, box = frame_and_box("close_water-bottle_chair_01")  # a tall, narrow crop

    card = card_photo(crop(frame, box), *CARD, AREA)

    assert card.circle is None
    with Image.open(io.BytesIO(card.jpeg)) as image:
        assert image.size == CARD
        for corner in ((5, 5), (1275, 5), (5, 715), (1275, 715)):
            assert image.getpixel(corner) == pytest.approx(CARD_BACKGROUND, abs=6)
        middle = image.getpixel(((AREA[0] + AREA[2]) // 2, (AREA[1] + AREA[3]) // 2))
        assert middle != pytest.approx(CARD_BACKGROUND, abs=6)


def test_without_an_area_smaller_than_the_card_a_16_9_photo_fills_it() -> None:
    frame, box = frame_and_box("medium_watch_chair_01")  # the room page asks for 640 x 360

    card = card_photo(moment_photo(frame, box), 640, 360, (0, 0, 640, 360))

    with Image.open(io.BytesIO(card.jpeg)) as image:
        assert image.size == (640, 360)
        for corner in ((3, 3), (636, 3), (3, 356), (636, 356)):
            assert image.getpixel(corner) != pytest.approx(CARD_BACKGROUND, abs=6)


def test_card_photo_raises_for_something_that_is_not_an_image() -> None:
    with pytest.raises(OSError):
        card_photo(b"not an image", *CARD, AREA)
