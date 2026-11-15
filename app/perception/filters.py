"""Cheap checks before any model sees a frame: blur and duplicate (perception rules).

Both work on small grayscale copies at a fixed size, so the cuts do not depend on the camera's
resolution and a check costs a few milliseconds.

- Sharpness: variance of the Laplacian of the frame at BLUR_SIDE px on its long side. A frame
  below the blur cut is smeared by motion and is dropped.
- Similarity: mean SSIM over 8 x 8 blocks of the frame at SSIM_SIDE px, against the last frame
  this device had accepted. At or above the duplicate cut the camera has not moved and the frame
  is dropped, with two exceptions (`FrameGate.check`).
"""

import io
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import numpy as np
from PIL import Image

from app.perception.frame import Frame

BLUR_SIDE = 640
SSIM_SIDE = 192
SSIM_BLOCK = 8
_C1 = (0.01 * 255) ** 2  # the SSIM paper's constants for 8-bit images
_C2 = (0.03 * 255) ** 2


def _gray(frame: Frame, side: int) -> np.ndarray:
    with Image.open(io.BytesIO(frame.jpeg)) as image:
        small = image.convert("L")
        small.thumbnail((side, side))
        return np.asarray(small, dtype=np.float64)


def sharpness(frame: Frame) -> float:
    """Variance of the 4-neighbour Laplacian. Higher is sharper."""
    g = _gray(frame, BLUR_SIDE)
    lap = g[1:-1, :-2] + g[1:-1, 2:] + g[:-2, 1:-1] + g[2:, 1:-1] - 4 * g[1:-1, 1:-1]
    return float(lap.var())


def thumbnail(frame: Frame) -> np.ndarray:
    """What similarity() compares: kept per device instead of the whole last frame."""
    return _gray(frame, SSIM_SIDE)


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Mean SSIM over SSIM_BLOCK-pixel blocks; 1.0 for identical, 0.0 when shapes differ."""
    if a.shape != b.shape:
        return 0.0
    h, w = (a.shape[0] // SSIM_BLOCK) * SSIM_BLOCK, (a.shape[1] // SSIM_BLOCK) * SSIM_BLOCK
    if h == 0 or w == 0:
        return 0.0

    def blocks(x: np.ndarray) -> np.ndarray:
        x = x[:h, :w].reshape(h // SSIM_BLOCK, SSIM_BLOCK, w // SSIM_BLOCK, SSIM_BLOCK)
        return x.transpose(0, 2, 1, 3).reshape(-1, SSIM_BLOCK * SSIM_BLOCK)

    x, y = blocks(a), blocks(b)
    mx, my = x.mean(axis=1), y.mean(axis=1)
    vx, vy = x.var(axis=1), y.var(axis=1)
    cov = ((x - mx[:, None]) * (y - my[:, None])).mean(axis=1)
    ssim = ((2 * mx * my + _C1) * (2 * cov + _C2)) / ((mx**2 + my**2 + _C1) * (vx + vy + _C2))
    return float(ssim.mean())


FilterResult = Literal["ok", "blurry", "duplicate"]


@dataclass
class FilterVerdict:
    result: FilterResult
    sharpness: float
    similarity: float | None  # None when there was no earlier frame to compare with


@dataclass
class FrameGate:
    """Per-device filter state. Not thread-safe; the worker runs on one event loop.

    A duplicate is still kept when:
    - the last accepted frame logged a sighting (`second_look_due`): that stay may still be
      tentative, and this frame is the second look the two-frame rule needs (perception rules);
    - the last accepted frame is at least `refresh_s` old by capture time: a camera left looking
      at an empty landmark must keep sending looks, or `mark_absent` never sees it empty.
    """

    blur_cut: float
    duplicate_cut: float
    refresh_s: float
    last_thumb: np.ndarray | None = None
    last_accepted_at: datetime | None = None
    second_look_due: bool = False

    def check(self, frame: Frame, captured_at: datetime) -> FilterVerdict:
        sharp = sharpness(frame)
        if sharp < self.blur_cut:
            return FilterVerdict("blurry", sharp, None)
        thumb = thumbnail(frame)
        same = None if self.last_thumb is None else similarity(thumb, self.last_thumb)
        if same is not None and same >= self.duplicate_cut:
            stale = self.last_accepted_at is not None and (
                (captured_at - self.last_accepted_at).total_seconds() >= self.refresh_s
            )
            if not (self.second_look_due or stale):
                return FilterVerdict("duplicate", sharp, same)
            self.second_look_due = False
        self.last_thumb = thumb
        self.last_accepted_at = captured_at
        return FilterVerdict("ok", sharp, same)
