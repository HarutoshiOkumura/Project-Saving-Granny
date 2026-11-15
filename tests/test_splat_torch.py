"""`TorchScene` must give what `NumpyScene` gives. Runs wherever torch is installed (the GPU
machine: `python -m pytest tests/test_splat_torch.py`); skipped in the backend's environment."""

import numpy as np
import pytest

from splat.model import MockModel, Reconstruction
from splat.scene import NumpyScene, TorchScene, scene_of

torch = pytest.importorskip("torch")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
KEYS = ("positions", "scales", "rotations", "opacities", "colors")


def _raw() -> Reconstruction:
    """The mock room with unequal scales, real rotations, some faint and some broken rows."""
    raw = MockModel(gaussians=30_000).reconstruct(np.zeros((5, 448, 448, 3), dtype=np.uint8))
    rng = np.random.default_rng(4)
    count = len(raw.means)
    raw.scales = np.exp(rng.uniform(-6, -3, (count, 3))).astype(np.float32)
    rotations = rng.normal(size=(count, 4)).astype(np.float32)
    raw.rotations = rotations / np.linalg.norm(rotations, axis=1, keepdims=True)
    raw.opacities[::7] = 0.001  # below the cut
    raw.means[5] = np.nan
    roll = np.deg2rad(20)  # a tilted phone, so levelling does real work
    turn = np.array(
        [[np.cos(roll), -np.sin(roll), 0], [np.sin(roll), np.cos(roll), 0], [0, 0, 1]],
        dtype=np.float32,
    )
    raw.camera_to_world[:, :3, :3] = raw.camera_to_world[:, :3, :3] @ turn
    return raw


def _on_device(raw: Reconstruction) -> Reconstruction:
    return Reconstruction(**{k: torch.as_tensor(v, device=DEVICE) for k, v in vars(raw).items()})


@pytest.fixture(scope="module")
def scenes() -> tuple[NumpyScene, TorchScene]:
    raw = _raw()
    return NumpyScene(raw, 0.02), TorchScene(_on_device(raw), 0.02)


def test_scene_of_picks_by_what_the_model_returned() -> None:
    raw = _raw()
    assert isinstance(scene_of(raw, 0.02), NumpyScene)
    assert isinstance(scene_of(_on_device(raw), 0.02), TorchScene)


def test_filtering_and_cameras_match(scenes: tuple[NumpyScene, TorchScene]) -> None:
    reference, fast = scenes
    assert fast.total == reference.total < 30_000
    for a, b in zip(reference.cameras, fast.cameras, strict=True):
        assert np.allclose(a.eye, b.eye, atol=1e-5) and np.allclose(a.up, b.up, atol=1e-5)
    assert np.allclose(reference.sample(500), fast.sample(500), atol=1e-4)


def test_every_gaussian_matches(scenes: tuple[NumpyScene, TorchScene]) -> None:
    reference, fast = scenes
    a, b = reference.best(reference.total), fast.best(fast.total)
    for key in KEYS:
        assert a[key].shape == b[key].shape, key
        assert np.allclose(a[key], b[key], atol=1e-4), key


def test_the_best_gaussians_match(scenes: tuple[NumpyScene, TorchScene]) -> None:
    reference, fast = scenes
    a, b = reference.best(5_000), fast.best(5_000)
    assert len(b["positions"]) == 5_000
    # Ties in importance may fall either way; nearly all rows must be the same Gaussians.
    same = (np.abs(a["positions"] - b["positions"]).max(axis=1) < 1e-4).mean()
    assert same > 0.99


def test_the_coarse_copy_matches(scenes: tuple[NumpyScene, TorchScene]) -> None:
    reference, fast = scenes
    a, b = reference.coarse(3_000), fast.coarse(3_000)
    assert abs(len(a["positions"]) - len(b["positions"])) <= 0.02 * len(a["positions"])
    assert a["scales"][0, 0] == pytest.approx(b["scales"][0, 0], rel=0.02)
    if len(a["positions"]) == len(b["positions"]):
        order_a = np.lexsort(a["positions"].round(3).T)
        order_b = np.lexsort(b["positions"].round(3).T)
        close = np.abs(a["positions"][order_a] - b["positions"][order_b]).max(axis=1) < 2e-3
        assert close.mean() > 0.98
    assert np.allclose(a["colors"].mean(axis=0), b["colors"].mean(axis=0), atol=1e-2)
    assert fast.coarse(10**9)["positions"].shape[0] == fast.total  # nothing to thin
