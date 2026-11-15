"""The model behind the builder: photos in, Gaussians and cameras out.

`AnySplatModel` runs AnySplat (github.com/OpenRobotLab/AnySplat, MIT) on a CUDA GPU: one forward
pass, no per-scene training, which is what makes the build take seconds. `MockModel` needs no
GPU and no weights; it returns a small made-up room so the server, the client and the viewer can
be built and tested on a laptop.

What AnySplat returns, read from its code on 15 Nov 2026 (`src/model/encoder/anysplat.py`,
`encoder/common/gaussian_adapter.py`):

- `gaussians.means` (1, N, 3) in the first photo's camera axes (x right, y down, z forward);
  `scales` (1, N, 3) are standard deviations, already activated; `rotations` (1, N, 4) are unit
  quaternions x, y, z, w; `opacities` (1, N) are 0..1; `harmonics` (1, N, 3, d_sh) with band 0
  first.
- `pred_context_pose["extrinsic"]` (1, V, 4, 4) is camera-to-world; `["intrinsic"]` (1, V, 3, 3)
  has its first row divided by the width and its second by the height.

Python 3.10 syntax; torch is imported only inside `AnySplatModel`.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np


@dataclass
class Reconstruction:
    """One scene in model axes, as the model left it: numpy arrays from the mock, torch tensors
    still on the GPU from AnySplat (`scene.py` works on either)."""

    means: np.ndarray  # (N, 3)
    scales: np.ndarray  # (N, 3) standard deviations
    rotations: np.ndarray  # (N, 4) x, y, z, w
    opacities: np.ndarray  # (N,) 0..1
    colors: np.ndarray  # (N, 3) SH band 0 coefficients
    camera_to_world: np.ndarray  # (V, 4, 4)
    intrinsics: np.ndarray  # (V, 3, 3) as fractions of the photo


class Model(Protocol):
    name: str

    def load(self) -> None: ...

    def reconstruct(self, images: np.ndarray) -> Reconstruction:
        """`images`: (V, side, side, 3) uint8, upright, at least 2 of them."""
        ...

    def describe(self) -> dict: ...


class AnySplatModel:
    name = "anysplat"

    def __init__(self, repo: Path, weights: str = "lhjiang/anysplat", device: str = "cuda") -> None:
        self.repo = repo
        self.weights = weights
        self.device = device
        self._model = None
        self._torch = None
        self.load_seconds: float | None = None

    def load(self) -> None:
        """Load the weights onto the GPU and run one small scene, so the first real build does
        not pay for CUDA start-up."""
        started = time.perf_counter()
        import torch

        if str(self.repo) not in sys.path:
            sys.path.insert(0, str(self.repo))  # AnySplat imports itself as `src.…`
        from src.model.model.anysplat import AnySplat

        model = AnySplat.from_pretrained(self.weights).to(self.device).eval()
        for parameter in model.parameters():
            parameter.requires_grad = False
        model.encoder.distill = False  # the teacher network is for training only
        self._torch, self._model = torch, model
        self.reconstruct(
            np.random.default_rng(0).integers(0, 255, (2, 448, 448, 3), dtype=np.uint8)
        )
        self.load_seconds = time.perf_counter() - started

    def reconstruct(self, images: np.ndarray) -> Reconstruction:
        torch, model = self._torch, self._model
        if model is None:
            raise RuntimeError("call load() first")
        with torch.no_grad():
            batch = torch.from_numpy(images).to(self.device).permute(0, 3, 1, 2).float().div(255.0)
            output = model.encoder(batch.unsqueeze(0), global_step=0, visualization_dump=None)
            g, pose = output.gaussians, output.pred_context_pose

            result = Reconstruction(
                means=g.means[0].float(),
                scales=g.scales[0].float(),
                rotations=g.rotations[0].float(),
                opacities=g.opacities[0].float(),
                colors=g.harmonics[0, :, :, 0].float().contiguous(),
                camera_to_world=pose["extrinsic"][0],
                intrinsics=pose["intrinsic"][0],
            )
        del output, g, pose, batch
        return result

    def describe(self) -> dict:
        torch = self._torch
        gpu = (
            torch.cuda.get_device_name(0)
            if torch is not None and torch.cuda.is_available()
            else None
        )
        return {
            "model": self.name,
            "weights": self.weights,
            "gpu_name": gpu,
            "models_loaded": self._model is not None,
            "load_seconds": None if self.load_seconds is None else round(self.load_seconds, 1),
        }


class MockModel:
    """A made-up room, the same for every input apart from its colours: a floor, a back wall
    and a table, with the cameras on an arc looking at the table. No GPU, a few milliseconds."""

    name = "mock"

    def __init__(self, gaussians: int = 60_000) -> None:
        self.gaussians = gaussians

    def load(self) -> None:
        return None

    def reconstruct(self, images: np.ndarray) -> Reconstruction:
        rng = np.random.default_rng(7)
        views = len(images)
        tint = images.reshape(-1, 3).mean(axis=0) / 255.0  # so different photos look different
        n_floor, n_wall = self.gaussians // 2, self.gaussians // 4
        n_table = self.gaussians - n_floor - n_wall

        # Model axes: x right, y down, z forward. The floor is 1.2 below the first camera.
        floor = np.column_stack(
            [rng.uniform(-2, 2, n_floor), np.full(n_floor, 1.2), rng.uniform(0.5, 5, n_floor)]
        )
        wall = np.column_stack(
            [rng.uniform(-2, 2, n_wall), rng.uniform(-1.3, 1.2, n_wall), np.full(n_wall, 5.0)]
        )
        table = np.column_stack(
            [
                rng.uniform(-0.6, 0.6, n_table),
                np.full(n_table, 0.45),
                rng.uniform(2.6, 3.4, n_table),
            ]
        )
        means = np.concatenate([floor, wall, table]).astype(np.float32)
        base = np.concatenate(
            [
                np.tile(0.55 * tint + 0.2, (n_floor, 1)),
                np.tile(0.35 * tint + 0.55, (n_wall, 1)),
                np.tile([0.55, 0.36, 0.2], (n_table, 1)),
            ]
        )
        rgb = np.clip(base + rng.normal(0, 0.04, base.shape), 0, 1)
        count = len(means)
        scales = np.full((count, 3), 0.03, dtype=np.float32)
        scales[:n_floor, 1] = 0.004  # flat on the floor
        scales[n_floor : n_floor + n_wall, 2] = 0.004  # flat on the wall
        scales[n_floor + n_wall :, 1] = 0.004
        rotations = np.tile(np.array([0, 0, 0, 1], dtype=np.float32), (count, 1))
        opacities = rng.uniform(0.6, 1.0, count).astype(np.float32)

        cameras = np.zeros((views, 4, 4), dtype=np.float32)
        target = np.array([0.0, 0.45, 3.0])
        for k in range(views):
            angle = np.deg2rad(-35 + 70 * (k / max(1, views - 1)))
            eye = target + np.array([np.sin(angle) * 3.0, -0.45, -np.cos(angle) * 3.0])
            forward = (target - eye) / np.linalg.norm(target - eye)
            right = np.cross(forward, [0.0, -1.0, 0.0])  # "up" is -y in these axes
            right /= np.linalg.norm(right)
            down = np.cross(forward, right)
            cameras[k, :3, 0], cameras[k, :3, 1], cameras[k, :3, 2] = right, down, forward
            cameras[k, :3, 3], cameras[k, 3, 3] = eye, 1.0
        intrinsics = np.tile(
            np.array([[0.9, 0, 0.5], [0, 0.9, 0.5], [0, 0, 1]], dtype=np.float32), (views, 1, 1)
        )
        return Reconstruction(
            means=means,
            scales=scales,
            rotations=rotations,
            opacities=opacities,
            colors=((rgb - 0.5) / 0.28209479177387814).astype(np.float32),
            camera_to_world=cameras,
            intrinsics=intrinsics,
        )

    def describe(self) -> dict:
        return {"model": self.name, "weights": None, "gpu_name": None, "models_loaded": True}
