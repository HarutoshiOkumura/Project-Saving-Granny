"""Frames in, crops out. Pure image work with Pillow; no network.

`load_frame()` makes every frame the same before any model sees it: upright (EXIF rotation
applied), long side at most 1920 px, JPEG with no metadata, so a phone photo's GPS never leaves
the backend. Boxes from Gemini and SAM 3 refer to this upright frame, and so do crops.
"""

import io
import math
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.perception.schema import Box

MAX_SIDE = 1920  # what the capture page sends, and what the step 04 bake-off measured
JPEG_QUALITY = 85

CROP_PAD = 0.15  # of the box's own width and height, on each side (perception rules)
CROP_MIN_PX = 64  # a tiny box still gives a photo someone can recognise
CROP_MAX_SIDE = 1024
CROP_MAX_BYTES = 1024 * 1024  # the `crops` bucket's cap (D17)

# JPEG header fields that carry no metadata about the person or place. Anything else (EXIF, XMP,
# comments, MPO pictures) means the file is re-encoded without it.
_HARMLESS_INFO = {
    "jfif",
    "jfif_density",
    "jfif_unit",
    "jfif_version",
    "dpi",
    "progressive",
    "progression",
    "adobe",
    "adobe_transform",
}


@dataclass(frozen=True)
class Frame:
    jpeg: bytes
    width: int
    height: int


def load_frame(data: bytes) -> Frame:
    """Raises PIL.UnidentifiedImageError (an OSError) when `data` is not an image.

    A file that already is what this makes, as the committed fixtures are, is kept byte for byte,
    so it is not compressed twice and the bake-off's cache keys still match.
    """
    with Image.open(io.BytesIO(data)) as raw:
        if (
            raw.format == "JPEG"
            and max(raw.size) <= MAX_SIDE
            and set(raw.info) <= _HARMLESS_INFO
            and not raw.getexif()
        ):
            return Frame(data, raw.width, raw.height)
        image = ImageOps.exif_transpose(raw).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    return Frame(_encode(image, JPEG_QUALITY), image.width, image.height)


def crop_pixels(frame: Frame, box: Box) -> tuple[int, int, int, int]:
    """`(left, top, right, bottom)` in pixels: the box padded by CROP_PAD of its size on each
    side, grown to at least CROP_MIN_PX around its centre, then clipped to the frame."""
    ymin, xmin, ymax, xmax = (v / 1000 for v in box)
    left, right = _padded(xmin * frame.width, xmax * frame.width, frame.width)
    top, bottom = _padded(ymin * frame.height, ymax * frame.height, frame.height)
    return left, top, right, bottom


def crop(frame: Frame, box: Box) -> bytes:
    """A JPEG of the item and a margin around it. Never the full frame unless the item fills it.

    The crop is scaled down to CROP_MAX_SIDE and stays under the bucket's 1 MiB cap.
    """
    with Image.open(io.BytesIO(frame.jpeg)) as image:
        piece = image.convert("RGB").crop(crop_pixels(frame, box))
    piece.thumbnail((CROP_MAX_SIDE, CROP_MAX_SIDE))
    for quality in (JPEG_QUALITY, 70, 50, 30):
        data = _encode(piece, quality)
        if len(data) <= CROP_MAX_BYTES:
            return data
    raise ValueError(f"crop is {len(data)} bytes even at quality 30")


def _padded(lo: float, hi: float, limit: int) -> tuple[int, int]:
    pad = (hi - lo) * CROP_PAD
    lo, hi = lo - pad, hi + pad
    if hi - lo < CROP_MIN_PX:
        middle = (lo + hi) / 2
        lo, hi = middle - CROP_MIN_PX / 2, middle + CROP_MIN_PX / 2
    start, end = max(0, math.floor(lo)), min(limit, math.ceil(hi))  # never cut into the margin
    if end <= start:  # a box wholly outside the frame still gives a pixel, never an error
        start = min(max(0, start), limit - 1)
        end = start + 1
    return start, end


def _encode(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    return buffer.getvalue()
