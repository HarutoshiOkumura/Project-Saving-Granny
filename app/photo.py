"""The photo a caller sees on FaceTime: the moment an item was last seen. Pure image work with
Pillow; no network.

Two pictures per look at an item:

- the tight crop (`app/perception/frame.py`): the item and a small margin, as before;
- the **moment photo** (`moment_photo`): the widest view around the item the rules allow, so the
  person can see what it is sitting on and what is around it. It is never the full frame: the
  window covers at most MOMENT_MAX_AREA of the frame unless the item itself is bigger than that.

The moment photo remembers where the item is inside it (a JPEG comment, `saveit-box:...`), so
the card can ring the item without a second lookup. `card_photo` turns either picture into the
exact frame the FaceTime agent sends as its video, showing the whole picture: the first version
(15 Nov) filled the card and zoomed, and a test call showed that left too little of the room.
"""

import io
from dataclasses import dataclass

from PIL import Image

from app.perception.frame import Frame
from app.perception.schema import Box

MOMENT_ASPECT = 16 / 9  # the card's photo area above its text band, and the room page's picture
MOMENT_MAX_AREA = 0.5  # of the frame. The window is as large as this allows: never the full frame
MOMENT_ITEM_PAD = 1.15  # an item bigger than the window still fits, with this much room around it
MOMENT_MAX_SIDE = 960  # px: about what the card shows it at, so it is not blown up and blurred
MOMENT_QUALITY = 60
MOMENT_MAX_BYTES = 1024 * 1024  # the `crops` bucket's cap (D17)

BOX_TAG = b"saveit-box:"  # then ymin,xmin,ymax,xmax on 0..1000 of this photo

CARD_QUALITY = 72
CARD_BACKGROUND = (6, 14, 18)  # the card's dark panel colour (agent/card.mjs)
RING_MIN_PX = 54  # the ring never hugs a tiny item
RING_PAD = 1.25  # of the item's half diagonal
RING_MAX_SHARE = 0.4  # an item wider or taller than this share of the photo needs no ring
RING_MAX_RADIUS = 0.3  # of the photo area's height: a ring points at a thing, it does not frame it


@dataclass(frozen=True)
class CardPhoto:
    """A JPEG exactly the card's size, and where to draw the ring (card pixels), if known."""

    jpeg: bytes
    circle: tuple[int, int, int] | None  # centre x, centre y, radius


def moment_window(frame: Frame, box: Box) -> tuple[int, int, int, int]:
    """`(left, top, right, bottom)` in frame pixels: the largest 16:9 window the frame and
    MOMENT_MAX_AREA allow (the whole width of an upright phone frame), centred on the item and
    moved, never shrunk, to stay inside the frame."""
    ymin, xmin, ymax, xmax = (v / 1000 for v in box)
    item_w, item_h = (xmax - xmin) * frame.width, (ymax - ymin) * frame.height
    most = MOMENT_MAX_AREA * frame.width * frame.height
    width = min(frame.width, frame.height * MOMENT_ASPECT, (most * MOMENT_ASPECT) ** 0.5)
    height = width / MOMENT_ASPECT
    # An item that fills more than the window allows still has to be in the picture.
    width = min(frame.width, max(width, item_w * MOMENT_ITEM_PAD))
    height = min(frame.height, max(height, item_h * MOMENT_ITEM_PAD))
    left = _slide((xmin + xmax) / 2 * frame.width - width / 2, width, frame.width)
    top = _slide((ymin + ymax) / 2 * frame.height - height / 2, height, frame.height)
    return round(left), round(top), round(left + width), round(top + height)


def moment_photo(frame: Frame, box: Box) -> bytes:
    """The moment photo for one item in one frame: a small JPEG that carries the item's box."""
    left, top, right, bottom = moment_window(frame, box)
    with Image.open(io.BytesIO(frame.jpeg)) as image:
        piece = image.convert("RGB").crop((left, top, right, bottom))
    piece.thumbnail((MOMENT_MAX_SIDE, MOMENT_MAX_SIDE))
    ymin, xmin, ymax, xmax = box
    width, height = right - left, bottom - top
    inside = (
        _mille((ymin / 1000 * frame.height - top) / height),
        _mille((xmin / 1000 * frame.width - left) / width),
        _mille((ymax / 1000 * frame.height - top) / height),
        _mille((xmax / 1000 * frame.width - left) / width),
    )
    comment = BOX_TAG + ",".join(str(v) for v in inside).encode()
    for quality in (MOMENT_QUALITY, 45, 30, 20):
        data = _encode(piece, quality, comment)
        if len(data) <= MOMENT_MAX_BYTES:
            return data
    raise ValueError(f"moment photo is {len(data)} bytes even at quality 20")


def read_box(jpeg: bytes) -> Box | None:
    """Where the item is in a moment photo (0..1000), or None for any other picture."""
    try:
        with Image.open(io.BytesIO(jpeg)) as image:
            comment = image.info.get("comment")
    except OSError:
        return None
    if isinstance(comment, str):
        comment = comment.encode()
    if not isinstance(comment, bytes) or not comment.startswith(BOX_TAG):
        return None
    try:
        ymin, xmin, ymax, xmax = (float(v) for v in comment[len(BOX_TAG) :].split(b","))
    except ValueError:
        return None
    if not (0 <= ymin < ymax <= 1000 and 0 <= xmin < xmax <= 1000):
        return None
    return (ymin, xmin, ymax, xmax)


def card_photo(jpeg: bytes, width: int, height: int, area: tuple[int, int, int, int]) -> CardPhoto:
    """`jpeg` as a `width` x `height` picture for the FaceTime card.

    `area` is `(left, top, right, bottom)` in card pixels: the part of the card the caller surely
    sees and that no text covers. The whole picture is shown there, as large as it fits and never
    cut, on the card's dark background, so nothing of the scene is lost to zooming. For a moment
    photo the ring's place is returned too (no ring when the item fills the picture); an older
    tight crop has none.

    Raises OSError when `jpeg` is not an image.
    """
    box = read_box(jpeg)
    with Image.open(io.BytesIO(jpeg)) as raw:
        image = raw.convert("RGB")
    room_w, room_h = area[2] - area[0], area[3] - area[1]
    scale = min(room_w / image.width, room_h / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    left, top = area[0] + (room_w - size[0]) // 2, area[1] + (room_h - size[1]) // 2
    card = Image.new("RGB", (width, height), CARD_BACKGROUND)
    card.paste(image.resize(size, Image.Resampling.LANCZOS), (left, top))
    encoded = _encode(card, CARD_QUALITY)
    if box is None:
        return CardPhoto(encoded, None)
    ymin, xmin, ymax, xmax = (v / 1000 for v in box)
    if xmax - xmin > RING_MAX_SHARE or ymax - ymin > RING_MAX_SHARE:
        return CardPhoto(encoded, None)  # the item fills the picture
    reach = ((xmax - xmin) ** 2 * size[0] ** 2 + (ymax - ymin) ** 2 * size[1] ** 2) ** 0.5 / 2
    radius = max(RING_MIN_PX, min(RING_PAD * reach, RING_MAX_RADIUS * room_h))
    centre = (left + (xmin + xmax) / 2 * size[0], top + (ymin + ymax) / 2 * size[1])
    return CardPhoto(encoded, (round(centre[0]), round(centre[1]), round(radius)))


def _slide(start: float, size: float, limit: float) -> float:
    """Where a window of `size` starts so that it lies inside 0..limit (`size` <= `limit`)."""
    return min(max(start, 0.0), max(0.0, limit - size))


def _mille(share: float) -> int:
    return round(min(max(share, 0.0), 1.0) * 1000)


def _encode(image: Image.Image, quality: int, comment: bytes | None = None) -> bytes:
    buffer = io.BytesIO()
    if comment is None:
        image.save(buffer, "JPEG", quality=quality)
    else:
        image.save(buffer, "JPEG", quality=quality, comment=comment)
    return buffer.getvalue()
