"""A reconstructed scene, ready to be cut into files: filtered, turned into level viewer axes,
and able to hand out a coarse copy or its best Gaussians.

Two classes with the same methods:

- `NumpyScene` works on the CPU. The mock model and the tests use it, and it is the reference.
- `TorchScene` does the same arithmetic on the GPU, where AnySplat's output already is. For a
  32-photo scene (3 million Gaussians) that takes the work after the model from about 1.9 s to
  under 0.2 s. `tests/test_splat_torch.py` checks it against `NumpyScene` wherever torch is
  installed.

`scene_of()` picks by what the model returned. Python 3.10 syntax; torch is imported only inside
`TorchScene`.
"""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np

from splat import geometry
from splat.model import Reconstruction

Arrays = dict[str, np.ndarray]  # positions, scales, rotations, opacities, colors: what spz takes


class Scene(Protocol):
    total: int  # Gaussians after filtering
    cameras: list[geometry.Camera]  # in level viewer axes

    def sample(self, count: int) -> np.ndarray:
        """About `count` positions spread through the scene, for bounds and views."""
        ...

    def best(self, count: int) -> Arrays:
        """The `count` Gaussians that add most to the picture, in the model's order."""
        ...

    def coarse(self, count: int) -> Arrays:
        """About `count` blobs that still cover every surface (`geometry.thin`)."""
        ...

    def release(self) -> None:
        """Give back whatever memory the scene holds."""
        ...


class NumpyScene:
    def __init__(self, raw: Reconstruction, min_opacity: float) -> None:
        keep = (
            np.isfinite(raw.means).all(axis=1)
            & np.isfinite(raw.scales).all(axis=1)
            & (raw.opacities >= min_opacity)
        )
        orientation = geometry.Orientation.from_cameras(raw.camera_to_world)
        self.cameras = [
            orientation.camera(c2w, k)
            for c2w, k in zip(raw.camera_to_world, raw.intrinsics, strict=True)
        ]
        self.positions = orientation.points(raw.means[keep])
        self.rotations = orientation.rotations(raw.rotations[keep])
        self.scales = raw.scales[keep]
        self.opacities = raw.opacities[keep]
        self.colors = raw.colors[keep]
        self.total = len(self.positions)

    def sample(self, count: int) -> np.ndarray:
        return self.positions[:: max(1, self.total // count)]

    def best(self, count: int) -> Arrays:
        if count >= self.total:
            index: Any = slice(None)
        else:
            weight = geometry.importance(self.scales, self.opacities)
            index = np.sort(np.argpartition(-weight, count - 1)[:count])
        return {
            "positions": self.positions[index],
            "scales": self.scales[index],
            "rotations": self.rotations[index],
            "opacities": self.opacities[index],
            "colors": self.colors[index],
        }

    def coarse(self, count: int) -> Arrays:
        thinned = geometry.thin(self.positions, self.opacities, self.colors, count)
        return thinned if thinned is not None else self.best(self.total)

    def release(self) -> None:
        return None


class TorchScene:
    """`NumpyScene` on whatever device the model's tensors are on."""

    def __init__(self, raw: Reconstruction, min_opacity: float) -> None:
        import torch

        self._torch = torch
        means = raw.means
        keep = (
            torch.isfinite(means).all(dim=1)
            & torch.isfinite(raw.scales).all(dim=1)
            & (raw.opacities >= min_opacity)
        )
        camera_to_world = raw.camera_to_world.detach().double().cpu().numpy()
        intrinsics = raw.intrinsics.detach().double().cpu().numpy()
        orientation = geometry.Orientation.from_cameras(camera_to_world)
        self.cameras = [
            orientation.camera(c2w, k) for c2w, k in zip(camera_to_world, intrinsics, strict=True)
        ]

        def tensor(values: np.ndarray) -> Any:
            return torch.as_tensor(values, dtype=means.dtype, device=means.device)

        flip = tensor(np.array([1.0, -1.0, -1.0]))
        self.positions = (means[keep] * flip) @ tensor(orientation.level).T
        level = tensor(geometry._quat_from_matrix(orientation.level))
        q = raw.rotations[keep] * tensor(np.array([1.0, -1.0, -1.0, 1.0]))
        ax, ay, az, aw = level[0], level[1], level[2], level[3]
        bx, by, bz, bw = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
        self.rotations = torch.stack(  # geometry._quat_multiply(level, q)
            [
                aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
                aw * bw - ax * bx - ay * by - az * bz,
            ],
            dim=1,
        )
        self.scales = raw.scales[keep]
        self.opacities = raw.opacities[keep]
        self.colors = raw.colors[keep]
        self.total = int(self.positions.shape[0])

    def sample(self, count: int) -> np.ndarray:
        return self.positions[:: max(1, self.total // count)].cpu().numpy()

    def best(self, count: int) -> Arrays:
        torch = self._torch
        if count >= self.total:
            index: Any = slice(None)
        else:
            smallest = self.scales.min(dim=1).values.clamp_min(1e-12)
            weight = self.opacities * self.scales.prod(dim=1) / smallest
            index = torch.topk(weight, count, sorted=False).indices.sort().values
        return {
            "positions": self.positions[index].cpu().numpy(),
            "scales": self.scales[index].cpu().numpy(),
            "rotations": self.rotations[index].cpu().numpy(),
            "opacities": self.opacities[index].cpu().numpy(),
            "colors": self.colors[index].cpu().numpy(),
        }

    def coarse(self, count: int) -> Arrays:
        """`geometry.thin`, line for line, on the device."""
        torch = self._torch
        if self.total <= count:
            return self.best(self.total)
        positions = self.positions
        low = positions.min(dim=0).values
        sample = self.sample(20_000)
        span = np.maximum(
            np.quantile(sample, 0.98, axis=0) - np.quantile(sample, 0.02, axis=0), 1e-6
        )
        area = 2 * (span[0] * span[1] + span[1] * span[2] + span[0] * span[2])
        cell = float(np.sqrt(area / count))

        def keys(size: float) -> Any:
            index = torch.floor((positions - low) / size).to(torch.int64)
            index.clamp_(0, (1 << geometry._AXIS_BITS) - 1)
            bits = geometry._AXIS_BITS
            return (index[:, 0] << (2 * bits)) | (index[:, 1] << bits) | index[:, 2]

        occupied = int(torch.unique(keys(cell)).numel())
        cell *= float(np.sqrt(occupied / count))
        _, inverse = torch.unique(keys(cell), return_inverse=True)
        cells = int(inverse.max().item()) + 1

        weight = self.opacities.double()
        total = torch.zeros(cells, dtype=torch.float64, device=positions.device)
        total.index_add_(0, inverse, weight).clamp_(min=1e-12)

        def mean(values: Any) -> np.ndarray:
            summed = torch.zeros(cells, 3, dtype=torch.float64, device=positions.device)
            summed.index_add_(0, inverse, values.double() * weight[:, None])
            return (summed / total[:, None]).float().cpu().numpy()

        rotations = np.zeros((cells, 4), dtype=np.float32)
        rotations[:, 3] = 1.0
        return {
            "positions": mean(positions),
            "scales": np.full((cells, 3), cell * geometry.BLOB, dtype=np.float32),
            "rotations": rotations,
            "opacities": total.clamp(max=0.98).float().cpu().numpy(),
            "colors": mean(self.colors),
        }

    def release(self) -> None:
        self.positions = self.rotations = self.scales = self.opacities = self.colors = None
        if self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()


def scene_of(raw: Reconstruction, min_opacity: float) -> Scene:
    return (
        NumpyScene(raw, min_opacity)
        if isinstance(raw.means, np.ndarray)
        else TorchScene(raw, min_opacity)
    )
