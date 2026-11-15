"""Choosing and preparing the photos a splat is built from. Pillow and numpy only.

Used on both sides: `scripts/build_room.py` picks and shrinks the frames on the laptop, so only
a megabyte or two crosses the network, and the server does the same to frames sent as they are.

Python 3.10 syntax: this also runs in the GPU machine's AnySplat environment.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

SIDE = 448  # AnySplat's input: a 448 x 448 square (its `process_image`)
SHARPNESS_SIDE = 640  # the blur score is measured at this size, as app/perception/filters.py does
JPEG_QUALITY = 90


def open_upright(data: bytes) -> Image.Image:
    """The photo as RGB with its EXIF rotation applied. Raises OSError when it is not an image."""
    with Image.open(io.BytesIO(data)) as raw:
        return ImageOps.exif_transpose(raw).convert("RGB")


def sharpness(image: Image.Image) -> float:
    """Variance of the 4-neighbour Laplacian at SHARPNESS_SIDE px. Higher is sharper."""
    small = image.convert("L")
    small.thumbnail((SHARPNESS_SIDE, SHARPNESS_SIDE))
    g = np.asarray(small, dtype=np.float64)
    if g.shape[0] < 3 or g.shape[1] < 3:
        return 0.0
    lap = g[1:-1, :-2] + g[1:-1, 2:] + g[:-2, 1:-1] + g[2:, 1:-1] - 4 * g[1:-1, 1:-1]
    return float(lap.var())


def pick(scores: list[float], count: int) -> list[int]:
    """Indexes of at most `count` frames: the sharpest one in each of `count` equal stretches.

    Even spacing keeps the whole walk covered; taking the sharpest inside each stretch drops the
    frames smeared by motion. The result is in capture order.
    """
    total = len(scores)
    if count <= 0 or total == 0:
        return []
    if total <= count:
        return list(range(total))
    chosen = []
    for k in range(count):
        start, end = (k * total) // count, ((k + 1) * total) // count
        chosen.append(max(range(start, end), key=lambda i: scores[i]))
    return chosen


def square_window(width: int, height: int) -> tuple[float, float, float, float]:
    """`(left, top, right, bottom)` of the centre square AnySplat sees, as fractions of the
    upright photo. A box in photo coordinates is mapped into the model's view with this."""
    if width >= height:
        margin = (width - height) / 2 / width
        return margin, 0.0, 1.0 - margin, 1.0
    margin = (height - width) / 2 / height
    return 0.0, margin, 1.0, 1.0 - margin


def prepare(image: Image.Image, side: int = SIDE) -> Image.Image:
    """Short side scaled to `side`, then the centre square: the geometry of AnySplat's own
    `process_image`, so cameras and boxes line up with what the model saw."""
    width, height = image.size
    if width >= height:
        size = (max(side, round(width * side / height)), side)
    else:
        size = (side, max(side, round(height * side / width)))
    resized = image.resize(size, Image.LANCZOS)
    left, top = (resized.width - side) // 2, (resized.height - side) // 2
    return resized.crop((left, top, left + side, top + side))


def to_jpeg(image: Image.Image, quality: int = JPEG_QUALITY) -> bytes:
    """A JPEG with no metadata (a phone photo's GPS never leaves the laptop)."""
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    return buffer.getvalue()


def is_prepared(image: Image.Image, side: int = SIDE) -> bool:
    return image.size == (side, side)
