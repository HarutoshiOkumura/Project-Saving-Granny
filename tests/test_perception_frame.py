"""Loading frames (EXIF rotation, size, metadata) and cropping (padding, bounds, size)."""

import io
import json

import pytest
from PIL import Image, UnidentifiedImageError

from app.perception.frame import (
    CROP_MAX_BYTES,
    CROP_MAX_SIDE,
    CROP_MIN_PX,
    MAX_SIDE,
    Frame,
    crop,
    crop_pixels,
    load_frame,
)
from tests.perception_fakes import FRAMES

GPS_IFD = 0x8825
ORIENTATION = 0x0112


def jpeg(width: int, height: int, orientation: int | None = None, gps: bool = False) -> bytes:
    """A test image whose left half is red and right half blue, so rotation is visible."""
    image = Image.new("RGB", (width, height), "blue")
    image.paste("red", (0, 0, width // 2, height))
    exif = Image.Exif()
    if orientation:
        exif[ORIENTATION] = orientation
    if gps:
        exif[GPS_IFD] = {1: "N", 2: (33.0, 47.0, 30.0)}
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=95, exif=exif.tobytes())
    return buffer.getvalue()


def frame(width: int = 800, height: int = 1600) -> Frame:
    return load_frame(jpeg(width, height))


def test_committed_fixture_frames_pass_byte_for_byte() -> None:
    for path in sorted(FRAMES.glob("*.jpg")):
        data = path.read_bytes()
        loaded = load_frame(data)
        assert loaded.jpeg == data
        assert max(loaded.width, loaded.height) <= MAX_SIDE


def test_exif_rotation_is_applied_and_all_metadata_dropped() -> None:
    # Orientation 6: the camera was turned; the stored pixels must be rotated 90 degrees clockwise.
    loaded = load_frame(jpeg(400, 200, orientation=6, gps=True))

    assert (loaded.width, loaded.height) == (200, 400)
    with Image.open(io.BytesIO(loaded.jpeg)) as image:
        assert not image.getexif()
        assert "exif" not in image.info
        # The red left half ends up on top after the clockwise turn.
        assert image.getpixel((100, 50))[0] > 200
        assert image.getpixel((100, 350))[2] > 200


def test_gps_alone_forces_a_reencode() -> None:
    data = jpeg(300, 200, gps=True)

    loaded = load_frame(data)

    assert loaded.jpeg != data
    with Image.open(io.BytesIO(loaded.jpeg)) as image:
        assert not image.getexif()


def test_big_frames_shrink_to_the_capture_size() -> None:
    loaded = load_frame(jpeg(4032, 3024))

    assert (loaded.width, loaded.height) == (MAX_SIDE, 1440)


def test_png_becomes_jpeg() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (50, 40), "green").save(buffer, "PNG")

    loaded = load_frame(buffer.getvalue())

    assert loaded.jpeg[:2] == b"\xff\xd8"
    assert (loaded.width, loaded.height) == (50, 40)


def test_not_an_image_raises() -> None:
    with pytest.raises(UnidentifiedImageError):
        load_frame(b"not a jpeg")


def test_crop_pads_fifteen_percent_of_the_box_on_each_side() -> None:
    # Box 160 px wide (x 320..480) and 320 px tall (y 640..960) on an 800 x 1600 frame.
    box = (400.0, 400.0, 600.0, 600.0)

    assert crop_pixels(frame(), box) == (296, 592, 504, 1008)


def test_crop_is_clipped_to_the_frame() -> None:
    # 52 px wide once padded, so it grows to 64 around x 780 first, then loses what is off-frame.
    assert crop_pixels(frame(), (0.0, 950.0, 100.0, 1000.0)) == (748, 0, 800, 184)


def test_a_tiny_box_grows_to_the_minimum_around_its_centre() -> None:
    left, top, right, bottom = crop_pixels(frame(), (500.0, 500.0, 501.0, 501.0))

    assert CROP_MIN_PX <= right - left <= CROP_MIN_PX + 1
    assert CROP_MIN_PX <= bottom - top <= CROP_MIN_PX + 1
    assert (left + right) / 2 == pytest.approx(400.4, abs=1)
    assert (top + bottom) / 2 == pytest.approx(800.8, abs=1)


def test_crop_returns_a_jpeg_of_that_area() -> None:
    data = crop(frame(), (400.0, 400.0, 600.0, 600.0))

    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "JPEG"
        assert image.size == (208, 416)
        assert not image.getexif()


def test_a_large_crop_is_scaled_down_and_stays_under_the_bucket_cap() -> None:
    data = crop(load_frame(jpeg(1920, 1440)), (0.0, 0.0, 1000.0, 1000.0))

    with Image.open(io.BytesIO(data)) as image:
        assert max(image.size) == CROP_MAX_SIDE
    assert len(data) <= CROP_MAX_BYTES


def test_noise_crop_still_fits_the_cap() -> None:
    noise = Image.effect_noise((1920, 1920), 120).convert("RGB")
    buffer = io.BytesIO()
    noise.save(buffer, "JPEG", quality=100)

    data = crop(load_frame(buffer.getvalue()), (0.0, 0.0, 1000.0, 1000.0))

    assert len(data) <= CROP_MAX_BYTES


def test_crop_of_a_fixture_frame_holds_the_hand_drawn_box() -> None:
    boxes = json.loads((FRAMES / "boxes.json").read_text())
    loaded = load_frame((FRAMES / "close_glasses_table_01.jpg").read_bytes())
    box = tuple(boxes["close_glasses_table_01"])

    left, top, right, bottom = crop_pixels(loaded, box)

    assert left <= box[1] / 1000 * loaded.width and right >= box[3] / 1000 * loaded.width
    assert top <= box[0] / 1000 * loaded.height and bottom >= box[2] / 1000 * loaded.height
    assert (right - left) * (bottom - top) < loaded.width * loaded.height  # never the full frame
