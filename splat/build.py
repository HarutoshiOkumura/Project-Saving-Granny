"""One build: photos -> the model -> two `.spz` files and the cameras, with a time per stage.

Two files come out because the network is usually the slow part, not the GPU:

- `preview.spz`: a coarse copy, one soft blob per grid cell (`geometry.thin`), about
  `preview_gaussians` of them. Under a megabyte, so it crosses a bad connection in seconds, and
  every surface is still there; the viewer shows it first.
- `full.spz`: the model's own Gaussians, the faintest and smallest dropped beyond
  `full_gaussians`. The viewer swaps it in when it has loaded. Asked for less than
  `KEEP_SHARE` of what the model made, it is a finer coarse copy instead, because dropping
  that many leaves holes.

Both are in level viewer axes (`geometry.py`), and so are the cameras in `cameras.json`. The
work between the model and the files (`scene.py`) runs where the model's output is: on the GPU
for AnySplat, in numpy for the mock. Frames are never written to disk here. Python 3.10 syntax.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from splat import frames as frame_tools
from splat import geometry, spz
from splat.model import Model
from splat.scene import Arrays, scene_of

MAX_FRAMES = 32  # what a 24 GB card takes at 448 px (the plan's figure); more on a bigger card
MIN_FRAMES = 2
PREVIEW_GAUSSIANS = 100_000  # about 0.8 MB
FULL_GAUSSIANS = 1_000_000  # about 13 MB; 0 keeps every Gaussian the model returns
KEEP_SHARE = 0.6  # below this share of the model's Gaussians, thin instead of dropping
MIN_OPACITY = 0.02  # fainter Gaussians are invisible and only cost bytes
SAMPLE = 20_000  # points used for the bounds and for where each camera was looking
FULL_GZIP = 1  # the model's Gaussians are near random bytes: level 6 saves 2% for 2 s more
COARSE_GZIP = 6  # a coarse copy is ordered by cell and compresses by a third


class BuildError(Exception):
    """The photos cannot make a scene (too few, or not images)."""


@dataclass
class Timer:
    stages: dict[str, float] = field(default_factory=dict)
    _last: float = field(default_factory=time.perf_counter)
    _start: float = field(default_factory=time.perf_counter)

    def mark(self, stage: str) -> None:
        now = time.perf_counter()
        self.stages[stage] = round((now - self._last) * 1000, 1)
        self._last = now

    def total_ms(self) -> float:
        return round((time.perf_counter() - self._start) * 1000, 1)


def _decode(data: bytes) -> tuple[np.ndarray, float, tuple[int, int]]:
    """One photo as the model's square, its sharpness, and its upright size."""
    image = frame_tools.open_upright(data)
    size = image.size
    score = frame_tools.sharpness(image)
    square = image if frame_tools.is_prepared(image) else frame_tools.prepare(image)
    return np.asarray(square, dtype=np.uint8), score, size


def load_images(
    jpegs: list[bytes], max_frames: int = MAX_FRAMES
) -> tuple[np.ndarray, list[int], list[tuple[int, int]]]:
    """`(images, chosen, sizes)`: the stacked squares the model gets, which of the uploaded
    photos they are (indexes, capture order), and those photos' upright sizes."""
    if len(jpegs) < MIN_FRAMES:
        raise BuildError(f"need at least {MIN_FRAMES} photos, got {len(jpegs)}")
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            decoded = list(pool.map(_decode, jpegs))
    except OSError as exc:
        raise BuildError(f"a photo could not be read: {exc}") from exc
    chosen = frame_tools.pick([score for _, score, _ in decoded], max_frames)
    images = np.stack([decoded[i][0] for i in chosen])
    return images, chosen, [decoded[i][2] for i in chosen]


def build(
    jpegs: list[bytes],
    model: Model,
    out_dir: Path,
    *,
    max_frames: int = MAX_FRAMES,
    preview_gaussians: int = PREVIEW_GAUSSIANS,
    full_gaussians: int = FULL_GAUSSIANS,
    min_opacity: float = MIN_OPACITY,
    on_preview: Callable[[dict], None] | None = None,
) -> dict:
    """Build one scene into `out_dir` and return its description (also saved as `scene.json`).

    `on_preview` is called as soon as `preview.spz` and `cameras.json` are on disk, before the
    full file is written, so a waiting client can start downloading.
    """
    timer = Timer()
    out_dir.mkdir(parents=True, exist_ok=True)
    images, chosen, sizes = load_images(jpegs, max_frames)
    timer.mark("decode")

    scene = scene_of(model.reconstruct(images), min_opacity)
    timer.mark("model")
    total = scene.total
    if total == 0:
        raise BuildError("the model returned no visible Gaussians")
    cameras = scene.cameras
    n_full = total if full_gaussians <= 0 else min(full_gaussians, total)
    n_preview = min(preview_gaussians, n_full)

    def level(count: int) -> tuple[bytes, int]:
        """The `.spz` for one size, and how many Gaussians it holds."""
        whole = count >= total * KEEP_SHARE
        arrays: Arrays = scene.best(count) if whole else scene.coarse(count)
        data = spz.encode(**arrays, compresslevel=FULL_GZIP if whole else COARSE_GZIP)
        return data, len(arrays["positions"])

    sample = scene.sample(SAMPLE)
    low, high = np.quantile(sample, 0.02, axis=0), np.quantile(sample, 0.98, axis=0)
    description = {
        "model": model.name,
        "frames_received": len(jpegs),
        "frames_used": len(chosen),
        "chosen": chosen,
        "gaussians": {"model": int(total)},
        "bytes": {},
        "up": [0, 1, 0],
        "bounds": {
            "min": [round(float(v), 4) for v in low],
            "max": [round(float(v), 4) for v in high],
        },
        "start": geometry.view_of(cameras[0], sample),
        "cameras": [
            {
                "frame": int(index),
                "width": int(size[0]),
                "height": int(size[1]),
                "window": [round(v, 5) for v in frame_tools.square_window(*size)],
                **camera.to_json(),
                "view": geometry.view_of(camera, sample),
            }
            for index, size, camera in zip(chosen, sizes, cameras, strict=True)
        ],
    }

    data, description["gaussians"]["preview"] = level(n_preview)
    (out_dir / "preview.spz").write_bytes(data)
    description["bytes"]["preview"] = len(data)
    (out_dir / "cameras.json").write_text(json.dumps(description))
    timer.mark("preview")
    description["timings_ms"] = {**timer.stages, "to_preview": timer.total_ms()}
    if on_preview is not None:
        on_preview(description)

    data, description["gaussians"]["full"] = level(n_full)
    (out_dir / "full.spz").write_bytes(data)
    description["bytes"]["full"] = len(data)
    timer.mark("full")
    description["timings_ms"] = {
        **timer.stages,
        "to_preview": description["timings_ms"]["to_preview"],
        "total": timer.total_ms(),
    }
    scene.release()
    (out_dir / "cameras.json").write_text(json.dumps(description))
    (out_dir / "timings.json").write_text(json.dumps(description["timings_ms"]))
    return description
