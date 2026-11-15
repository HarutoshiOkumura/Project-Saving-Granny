"""The splat builder's pure parts and its server with the mock model. No GPU, no network."""

import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from splat import build, frames, geometry, spz
from splat.model import MockModel
from splat.server import create_app

FIXTURES = sorted((Path(__file__).parent / "fixtures" / "frames").glob("*.jpg"))


def _jpeg(width: int, height: int, seed: int = 0, blur: bool = False) -> bytes:
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    if blur:
        pixels[:] = pixels.mean(axis=(0, 1), keepdims=True).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, "JPEG", quality=90)
    return buffer.getvalue()


# ---- frames ------------------------------------------------------------------------------


def test_pick_takes_the_sharpest_frame_of_each_stretch_in_order() -> None:
    scores = [1, 9, 2, 3, 4, 8, 7, 1, 1]
    assert frames.pick(scores, 3) == [1, 5, 6]


def test_pick_keeps_everything_when_there_are_few_frames() -> None:
    assert frames.pick([3.0, 1.0], 32) == [0, 1]
    assert frames.pick([], 4) == []


def test_sharpness_ranks_a_flat_photo_below_a_detailed_one() -> None:
    sharp = frames.sharpness(frames.open_upright(_jpeg(320, 240)))
    flat = frames.sharpness(frames.open_upright(_jpeg(320, 240, blur=True)))
    assert sharp > 100 > flat


@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920), (448, 448), (300, 200)])
def test_prepare_gives_the_models_square(size: tuple[int, int]) -> None:
    square = frames.prepare(Image.new("RGB", size))
    assert square.size == (frames.SIDE, frames.SIDE)
    assert frames.is_prepared(square)


def test_square_window_is_the_centre_square_of_the_photo() -> None:
    left, top, right, bottom = frames.square_window(1920, 1080)
    assert (top, bottom) == (0.0, 1.0)
    assert left == pytest.approx(0.21875) and right == pytest.approx(0.78125)
    assert frames.square_window(1080, 1920)[1] == pytest.approx(0.21875)


def test_to_jpeg_drops_metadata() -> None:
    image = Image.new("RGB", (64, 64))
    exif = image.getexif()
    exif[0x010F] = "a phone"
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    cleaned = frames.to_jpeg(frames.open_upright(buffer.getvalue()))
    assert not Image.open(io.BytesIO(cleaned)).getexif()


# ---- spz ---------------------------------------------------------------------------------


def _cloud(count: int = 500) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(3)
    rotations = rng.normal(size=(count, 4))
    return {
        "positions": rng.uniform(-3, 3, (count, 3)),
        "scales": np.exp(rng.uniform(-7, -2, (count, 3))),
        "rotations": rotations / np.linalg.norm(rotations, axis=1, keepdims=True),
        "opacities": rng.uniform(0, 1, count),
        "colors": rng.uniform(-1.5, 1.5, (count, 3)),
    }


def _same_rotation(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """|a . b| per row: 1 when two unit quaternions are the same rotation (q and -q are)."""
    return np.abs((a * b).sum(axis=1))


@pytest.mark.parametrize("version", [2, 3])
def test_spz_round_trip(version: int) -> None:
    cloud = _cloud()
    back = spz.decode(spz.encode(**cloud, version=version))
    assert np.abs(back["positions"] - cloud["positions"]).max() <= 1 / 4096
    assert np.abs(back["opacities"] - cloud["opacities"]).max() <= 1 / 255
    assert np.abs(back["colors"] - cloud["colors"]).max() <= 0.5 / (255 * spz.COLOR_SCALE) + 1e-9
    assert np.abs(np.log(back["scales"]) - np.log(cloud["scales"])).max() <= 1 / 32 + 1e-9
    worst = _same_rotation(back["rotations"], cloud["rotations"]).min()
    assert worst > (0.9995 if version == 3 else 0.995)


def test_spz_header_is_the_reference_layout() -> None:
    import gzip
    import struct

    cloud = _cloud(7)
    body = gzip.decompress(spz.encode(**cloud))
    magic, version, count, sh_degree, fractional_bits, flags, reserved = struct.unpack_from(
        "<IIIBBBB", body
    )
    assert (magic, version, count) == (0x5053474E, 3, 7)
    assert (sh_degree, fractional_bits, flags, reserved) == (0, 12, 0, 0)
    assert len(body) == 16 + 7 * (9 + 1 + 3 + 3 + 4)
    assert body[:4] == b"NGSP"
    assert spz.count_of(spz.encode(**cloud)) == 7


def test_spz_packs_known_values_as_the_reference_encoder_does() -> None:
    import gzip

    data = spz.encode(
        positions=np.array([[1.0, -0.5, 0.25]]),
        scales=np.array([[1.0, 1.0, 1.0]]),
        rotations=np.array([[0.0, 0.0, 0.0, 1.0]]),
        opacities=np.array([1.0]),
        colors=np.array([[0.0, 0.0, 0.0]]),
        version=2,
    )
    body = gzip.decompress(data)[16:]
    assert body[0:3] == (4096).to_bytes(3, "little")  # x = 1.0 with 12 fractional bits
    assert body[3:6] == (-2048 & 0xFFFFFF).to_bytes(3, "little")  # y = -0.5, two's complement
    assert body[6:9] == (1024).to_bytes(3, "little")
    assert body[9] == 255  # opacity 1
    assert list(body[10:13]) == [128, 128, 128]  # a zero colour coefficient is mid grey
    assert list(body[13:16]) == [160, 160, 160]  # ln(1) = 0 -> (0 + 10) * 16
    assert list(body[16:19]) == [128, 128, 128]  # no rotation: x = y = z = 0


def test_spz_rejects_arrays_that_do_not_line_up() -> None:
    cloud = _cloud(5)
    cloud["scales"] = cloud["scales"][:4]
    with pytest.raises(ValueError, match="scales"):
        spz.encode(**cloud)


def test_rgb_and_sh_band_zero_are_inverses() -> None:
    rgb = np.array([[0.0, 0.5, 1.0]])
    assert np.allclose(spz.sh0_to_rgb(spz.rgb_to_sh0(rgb)), rgb)


# ---- geometry ----------------------------------------------------------------------------


def _camera_to_world(eye: np.ndarray, target: np.ndarray, roll_deg: float = 0.0) -> np.ndarray:
    """An OpenCV-style camera (x right, y down, z forward) at `eye` looking at `target`."""
    forward = (target - eye) / np.linalg.norm(target - eye)
    right = np.cross(forward, [0.0, -1.0, 0.0])
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    roll = np.deg2rad(roll_deg)
    right, down = (
        np.cos(roll) * right + np.sin(roll) * down,
        -np.sin(roll) * right + np.cos(roll) * down,
    )
    matrix = np.eye(4)
    matrix[:3, 0], matrix[:3, 1], matrix[:3, 2], matrix[:3, 3] = right, down, forward, eye
    return matrix


INTRINSIC = np.array([[0.9, 0, 0.5], [0, 0.9, 0.5], [0, 0, 1.0]])


def test_orientation_flips_to_viewer_axes() -> None:
    cameras = np.stack([_camera_to_world(np.zeros(3), np.array([0.0, 0.0, 3.0]))])
    orientation = geometry.Orientation.from_cameras(cameras)
    # A point below and ahead of the camera in model axes is below (-y) and ahead (-z) in viewer.
    assert np.allclose(orientation.points(np.array([[0.5, 1.0, 2.0]])), [[0.5, -1.0, -2.0]])
    camera = orientation.camera(cameras[0], INTRINSIC)
    assert np.allclose(camera.forward, [0, 0, -1]) and np.allclose(camera.up, [0, 1, 0])


def test_orientation_levels_a_tilted_first_photo() -> None:
    """Every camera rolled 25 degrees: afterwards their up is the viewer's +y again."""
    target = np.array([0.0, 0.0, 3.0])
    cameras = np.stack(
        [_camera_to_world(np.array([x, 0.0, 0.0]), target, roll_deg=25) for x in (-1.0, 0.0, 1.0)]
    )
    orientation = geometry.Orientation.from_cameras(cameras)
    ups = np.stack([orientation.camera(c, INTRINSIC).up for c in cameras])
    assert np.allclose(ups.mean(axis=0) / np.linalg.norm(ups.mean(axis=0)), [0, 1, 0], atol=1e-6)
    assert np.allclose(np.linalg.det(orientation.level), 1.0)


def test_rotated_gaussians_keep_their_shape_under_the_orientation() -> None:
    """Covariance through `Orientation` equals the covariance transformed directly."""
    rng = np.random.default_rng(5)
    cameras = np.stack([_camera_to_world(np.zeros(3), np.array([0.3, 0.2, 3.0]), roll_deg=20)])
    orientation = geometry.Orientation.from_cameras(cameras)
    q = rng.normal(size=(1, 4))
    q /= np.linalg.norm(q)
    scales = np.array([0.5, 0.1, 0.02])

    def matrix(quaternion: np.ndarray) -> np.ndarray:
        x, y, z, w = quaternion
        return np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ]
        )

    def covariance(rotation: np.ndarray) -> np.ndarray:
        return rotation @ np.diag(scales**2) @ rotation.T

    transform = orientation.level @ np.diag([1.0, -1.0, -1.0])
    expected = transform @ covariance(matrix(q[0])) @ transform.T
    got = covariance(matrix(orientation.rotations(q)[0]))
    assert np.allclose(got, expected, atol=1e-9)


def test_camera_projects_and_casts_rays_consistently() -> None:
    cameras = np.stack([_camera_to_world(np.array([1.0, -0.5, 0.0]), np.array([0.0, 0.0, 4.0]))])
    orientation = geometry.Orientation.from_cameras(cameras)
    camera = orientation.camera(cameras[0], INTRINSIC)
    point = camera.eye + 2.5 * camera.ray(0.3, 0.7)
    u, v, depth = camera.project(point[None, :])
    assert u[0] == pytest.approx(0.3) and v[0] == pytest.approx(0.7) and depth[0] > 0
    assert geometry.Camera.from_json(camera.to_json()).fx == pytest.approx(camera.fx)


def _table_scene() -> tuple[np.ndarray, geometry.Camera]:
    """A floor at y = -1 and a table top at y = -0.3 in front of a camera at the origin."""
    rng = np.random.default_rng(1)
    floor = np.column_stack(
        [rng.uniform(-3, 3, 8000), np.full(8000, -1.0), rng.uniform(-6, -1, 8000)]
    )
    table = np.column_stack(
        [rng.uniform(-0.4, 0.4, 4000), np.full(4000, -0.3), rng.uniform(-2.4, -1.6, 4000)]
    )
    cameras = np.stack([_camera_to_world(np.zeros(3), np.array([0.0, 0.3, 2.0]))])
    camera = geometry.Orientation(np.eye(3)).camera(cameras[0], INTRINSIC)
    return np.concatenate([floor, table]), camera


def test_pick_on_ray_lands_on_the_nearest_surface() -> None:
    points, camera = _table_scene()
    direction = np.array([0.0, -0.3, -2.0])  # at the middle of the table top
    hit = geometry.pick_on_ray(points, camera.eye, direction)
    assert hit is not None
    assert hit[1] == pytest.approx(-0.3, abs=0.02)  # the table, not the floor behind it
    assert abs(hit[0]) < 0.1 and -2.2 < hit[2] < -1.8


def test_pick_on_ray_misses_when_nothing_is_there() -> None:
    points, camera = _table_scene()
    assert geometry.pick_on_ray(points, camera.eye, np.array([0.0, 1.0, 0.0])) is None


def test_locate_box_finds_what_a_box_in_the_photo_shows() -> None:
    points, camera = _table_scene()
    u, v, _ = camera.project(np.array([[0.0, -0.3, -2.0]]))
    box = (u[0] - 0.05, v[0] - 0.05, u[0] + 0.05, v[0] + 0.05)
    spot = geometry.locate_box(points, camera, box)
    assert spot is not None and spot[1] == pytest.approx(-0.3, abs=0.02)
    assert geometry.locate_box(points, camera, (2.0, 2.0, 2.1, 2.1)) is None


def test_thin_keeps_surfaces_covered_near_the_asked_size() -> None:
    rng = np.random.default_rng(2)
    wall = np.column_stack(
        [rng.uniform(0, 4, 60_000), rng.uniform(0, 2, 60_000), np.zeros(60_000)]
    ).astype(np.float32)
    colors = np.tile(np.array([[0.4, -0.2, 0.1]], dtype=np.float32), (60_000, 1))
    coarse = geometry.thin(wall, np.full(60_000, 0.5, dtype=np.float32), colors, 2_000)
    assert coarse is not None
    assert 1_400 <= len(coarse["positions"]) <= 2_600
    assert np.allclose(coarse["colors"], [0.4, -0.2, 0.1], atol=1e-4)
    # No hole: every point of the wall has a blob within about one cell.
    cell = float(coarse["scales"][0, 0]) / geometry.BLOB
    probe = wall[::500]
    nearest = np.linalg.norm(probe[:, None, :] - coarse["positions"][None, :, :], axis=2).min(
        axis=1
    )
    assert nearest.max() < 1.5 * cell
    assert geometry.thin(wall[:100], np.ones(100), colors[:100], 2_000) is None


# ---- the build and the server, with the mock model -----------------------------------------


def test_build_writes_both_levels_and_cameras(tmp_path: Path) -> None:
    jpegs = [path.read_bytes() for path in FIXTURES[:5]]
    seen: list[dict] = []
    description = build.build(
        jpegs, MockModel(gaussians=20_000), tmp_path, max_frames=4, preview_gaussians=2_000,
        on_preview=seen.append,
    )  # fmt: skip
    assert description["frames_received"] == 5 and description["frames_used"] == 4
    assert len(description["cameras"]) == 4
    assert seen and (tmp_path / "preview.spz").exists()
    full = spz.decode((tmp_path / "full.spz").read_bytes())
    preview = spz.decode((tmp_path / "preview.spz").read_bytes())
    assert len(full["positions"]) == description["gaussians"]["full"] == 20_000
    assert len(preview["positions"]) == description["gaussians"]["preview"] < 4_000
    # Level viewer axes: the mock's floor is below the cameras, and the cameras look along -z.
    assert np.median(full["positions"][:, 1]) < description["cameras"][0]["eye"][1]
    assert description["cameras"][0]["up"][1] > 0.9
    assert description["start"]["target"][2] < description["start"]["eye"][2]
    assert set(description["timings_ms"]) >= {"decode", "model", "to_preview", "total"}
    assert not list(tmp_path.glob("*.jpg"))  # frames are never written to disk


def test_build_refuses_too_few_or_unreadable_photos(tmp_path: Path) -> None:
    with pytest.raises(build.BuildError, match="at least 2"):
        build.build([FIXTURES[0].read_bytes()], MockModel(), tmp_path)
    with pytest.raises(build.BuildError, match="could not be read"):
        build.build([b"not an image", b"nor this"], MockModel(), tmp_path)


@pytest.fixture
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("SPLAT_TOKEN", raising=False)
    with TestClient(create_app(MockModel(gaussians=8_000), tmp_path)) as client:
        yield client


def _files(count: int) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("frames", (f"{i}.jpg", FIXTURES[i].read_bytes(), "image/jpeg")) for i in range(count)]


def test_server_builds_in_one_request(server: TestClient) -> None:
    assert server.get("/health").json()["models_loaded"] is True
    scene = server.post("/build", files=_files(3), params={"preview_gaussians": 1_000}).json()
    assert scene["status"] in ("ready_preview", "ready") and scene["version"] >= 1
    scene_id = scene["scene_id"]
    preview = server.get(f"/scenes/{scene_id}/splat", params={"level": "preview"})
    assert preview.status_code == 200 and spz.count_of(preview.content) > 0
    for _ in range(100):
        scene = server.get(f"/scenes/{scene_id}").json()
        if scene["status"] == "ready":
            break
    assert scene["status"] == "ready" and scene["version"] == 2
    assert spz.count_of(server.get(f"/scenes/{scene_id}/splat").content) == 8_000
    assert len(server.get(f"/scenes/{scene_id}/cameras").json()["cameras"]) == 3
    assert server.delete(f"/scenes/{scene_id}").json() == {"deleted": True}
    assert server.get(f"/scenes/{scene_id}").status_code == 404


def test_server_takes_frames_as_they_are_taken(server: TestClient) -> None:
    scene_id = server.post("/scenes").json()["scene_id"]
    assert server.post(f"/scenes/{scene_id}/frames", files=_files(1)).json() == {"n_frames": 1}
    assert server.post(f"/scenes/{scene_id}/build").status_code == 422  # one photo is too few
    assert server.post(f"/scenes/{scene_id}/frames", files=_files(2)).json() == {"n_frames": 3}
    assert server.get(f"/scenes/{scene_id}/splat").status_code == 409  # not built yet
    built = server.post(f"/scenes/{scene_id}/build").json()
    assert built["status"] in ("ready_preview", "ready")
    assert server.post(f"/scenes/{scene_id}/frames", files=_files(1)).status_code == 409


def test_server_reports_a_failed_build(server: TestClient) -> None:
    bad = [("frames", (f"{i}.jpg", b"not an image", "image/jpeg")) for i in range(2)]
    scene = server.post("/build", files=bad).json()
    assert scene["status"] == "failed" and "could not be read" in scene["error"]


def test_server_checks_the_token_when_one_is_set(
    server: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPLAT_TOKEN", "splat_token_fake")
    assert server.post("/scenes").status_code == 401
    assert server.post("/scenes", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = server.post("/scenes", headers={"Authorization": "Bearer splat_token_fake"})
    assert ok.status_code == 200
    assert server.get("/health").status_code == 200  # health needs no token
