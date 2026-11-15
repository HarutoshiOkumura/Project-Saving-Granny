"""Every axis conversion and 3D lookup of the room scan, in one place. numpy only.

Three frames of reference meet here:

- **Model axes** (AnySplat, OpenCV style): x right, y down, z forward, in the first photo's
  camera. Cameras are camera-to-world matrices.
- **Viewer axes** (three.js, and what `.spz` stores): x right, y up, z back. `to_viewer` turns
  the model's output into them once, on the server; nothing downstream converts again.
- **Level**: the viewer axes turned so "up" is the average up of the cameras, which is how the
  phone was held. Without this the room opens tilted by however the first photo was tilted.

Everything after `Orientation.apply` is in level viewer axes: the `.spz`, `cameras.json`, the
pins in `landmarks.x/y/z`. Python 3.10 syntax.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_FLIP = np.array([1.0, -1.0, -1.0])  # model (right, down, forward) -> viewer (right, up, back)


def _quat_multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hamilton product of quaternions stored x, y, z, w; `a` then applies after `b`."""
    ax, ay, az, aw = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    bx, by, bz, bw = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack(
        [
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        ],
        axis=-1,
    )


def _quat_from_matrix(m: np.ndarray) -> np.ndarray:
    """A 3 x 3 rotation as x, y, z, w."""
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0:
        s = np.sqrt(trace + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [s / 4, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / s, s / 4, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, s / 4, (m[1, 0] - m[0, 1]) / s]
    return np.asarray(q, dtype=np.float64)


def rotation_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The smallest rotation (3 x 3) that turns direction `a` onto direction `b`."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    cross = np.cross(a, b)
    cosine = float(a @ b)
    if cosine > 1 - 1e-12:
        return np.eye(3)
    if cosine < -1 + 1e-12:  # opposite: half a turn about any axis square to `a`
        axis = np.cross(a, [1.0, 0.0, 0.0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0.0, 0.0, 1.0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0, -cross[2], cross[1]], [cross[2], 0, -cross[0]], [-cross[1], cross[0], 0]])
    return np.eye(3) + k + k @ k / (1 + cosine)


@dataclass(frozen=True)
class Camera:
    """One photo's camera in level viewer axes."""

    eye: np.ndarray  # (3,) where the camera stood
    right: np.ndarray  # (3,) unit vectors of the image: +x of the photo,
    up: np.ndarray  # up in the photo,
    forward: np.ndarray  # and the direction it looked
    fx: float  # focal lengths as fractions of the square photo's width and height
    fy: float
    cx: float  # principal point, same units (0.5 is the middle)
    cy: float

    def project(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """`(u, v, depth)` of each point: u and v as 0..1 across and down the photo, depth along
        the view. Points behind the camera get a depth of 0 or less."""
        rel = np.asarray(points, dtype=np.float64) - self.eye
        depth = rel @ self.forward
        safe = np.where(depth > 1e-9, depth, 1.0)
        u = self.cx + self.fx * (rel @ self.right) / safe
        v = self.cy - self.fy * (rel @ self.up) / safe
        return u, v, depth

    def ray(self, u: float, v: float) -> np.ndarray:
        """Unit direction through the photo at (u, v), each 0..1."""
        direction = (
            self.forward
            + self.right * ((u - self.cx) / self.fx)
            - self.up * ((v - self.cy) / self.fy)
        )
        return direction / np.linalg.norm(direction)

    def to_json(self) -> dict:
        return {
            "eye": [round(float(v), 5) for v in self.eye],
            "right": [round(float(v), 5) for v in self.right],
            "up": [round(float(v), 5) for v in self.up],
            "forward": [round(float(v), 5) for v in self.forward],
            "fx": round(self.fx, 5),
            "fy": round(self.fy, 5),
            "cx": round(self.cx, 5),
            "cy": round(self.cy, 5),
        }

    @classmethod
    def from_json(cls, data: dict) -> Camera:
        return cls(
            eye=np.asarray(data["eye"], dtype=np.float64),
            right=np.asarray(data["right"], dtype=np.float64),
            up=np.asarray(data["up"], dtype=np.float64),
            forward=np.asarray(data["forward"], dtype=np.float64),
            fx=float(data["fx"]),
            fy=float(data["fy"]),
            cx=float(data["cx"]),
            cy=float(data["cy"]),
        )


@dataclass(frozen=True)
class Orientation:
    """Model axes -> level viewer axes: flip y and z, then turn so the cameras' up is +y."""

    level: np.ndarray  # (3, 3) rotation applied after the flip

    @classmethod
    def from_cameras(cls, camera_to_world: np.ndarray) -> Orientation:
        """`camera_to_world`: (V, 4, 4) in model axes. The cameras' own "up" is their -y."""
        ups = -np.asarray(camera_to_world, dtype=np.float64)[:, :3, 1] * _FLIP
        mean = ups.sum(axis=0)
        if np.linalg.norm(mean) < 1e-6:
            return cls(np.eye(3))
        return cls(rotation_between(mean, np.array([0.0, 1.0, 0.0])))

    def points(self, model_points: np.ndarray) -> np.ndarray:
        """Float32 in, float32 out: a scene is a million rows and more."""
        points = np.asarray(model_points)
        kind = points.dtype if points.dtype == np.float32 else np.float64
        return (points * _FLIP.astype(kind)) @ self.level.T.astype(kind)

    def rotations(self, model_quaternions: np.ndarray) -> np.ndarray:
        """Gaussian orientations (x, y, z, w). Flipping y and z of the world turns a rotation R
        into F R F, which is the quaternion with y and z negated; then the level turn applies."""
        q = np.asarray(model_quaternions)
        kind = q.dtype if q.dtype == np.float32 else np.float64
        q = q * np.array([1.0, -1.0, -1.0, 1.0], dtype=kind)
        return _quat_multiply(_quat_from_matrix(self.level).astype(kind)[None, :], q)

    def camera(self, camera_to_world: np.ndarray, intrinsic: np.ndarray) -> Camera:
        """`intrinsic`: 3 x 3 with focal lengths and principal point as fractions of the photo
        (AnySplat's own normalization)."""
        c2w = np.asarray(camera_to_world, dtype=np.float64)
        k = np.asarray(intrinsic, dtype=np.float64)

        def direction(column: np.ndarray) -> np.ndarray:
            v = (column * _FLIP) @ self.level.T
            return v / np.linalg.norm(v)

        return Camera(
            eye=self.points(c2w[:3, 3][None, :])[0],
            right=direction(c2w[:3, 0]),
            up=direction(-c2w[:3, 1]),
            forward=direction(c2w[:3, 2]),
            fx=float(k[0, 0]),
            fy=float(k[1, 1]),
            cx=float(k[0, 2]),
            cy=float(k[1, 2]),
        )


def view_of(camera: Camera, points: np.ndarray) -> dict:
    """Where the viewer should stand to see what this photo saw: `eye`, and a `target` on the
    scene along the view (the median depth of the points in front of the camera)."""
    _u, _v, depth = camera.project(points)
    ahead = depth[depth > 0]
    distance = float(np.median(ahead)) if len(ahead) else 1.0
    target = camera.eye + camera.forward * distance
    return {
        "eye": [round(float(v), 5) for v in camera.eye],
        "target": [round(float(v), 5) for v in target],
    }


def locate_box(
    points: np.ndarray, camera: Camera, box: tuple[float, float, float, float], shrink: float = 0.5
) -> np.ndarray | None:
    """The 3D position of what a box in one photo shows, or None when no point lands in it.

    `box` is `(left, top, right, bottom)` as 0..1 of the square photo the model saw. Only the
    middle `shrink` of the box counts, so the table behind a pair of glasses mostly stays out;
    of the points that project there, the nearer half is the object and its median is the
    answer.
    """
    left, top, right, bottom = box
    cx, cy = (left + right) / 2, (top + bottom) / 2
    half_w, half_h = (right - left) * shrink / 2, (bottom - top) * shrink / 2
    u, v, depth = camera.project(points)
    inside = (depth > 0) & (np.abs(u - cx) <= half_w) & (np.abs(v - cy) <= half_h)
    if not inside.any():
        return None
    hits, depths = np.asarray(points)[inside], depth[inside]
    near = depths <= np.median(depths)
    return np.median(hits[near], axis=0)


def pick_on_ray(
    points: np.ndarray, origin: np.ndarray, direction: np.ndarray, width: float = 0.02
) -> np.ndarray | None:
    """The surface a tap in the 3D view lands on, or None when the ray passes nothing.

    Points within `width` (the tangent of the angle off the ray, so the cone grows with distance
    like a fingertip does) are candidates; the answer is the middle of the nearest clump, not
    the single nearest point, so one stray Gaussian floating in front does not win.
    """
    origin = np.asarray(origin, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    direction = direction / np.linalg.norm(direction)
    rel = np.asarray(points, dtype=np.float64) - origin
    along = rel @ direction
    off = np.linalg.norm(rel - along[:, None] * direction, axis=1)
    near = (along > 1e-6) & (off <= width * along)
    if near.sum() < 3:
        return None
    hits, depths = rel[near] + origin, along[near]
    front = np.quantile(depths, 0.1)
    clump = depths <= front * 1.08 + 1e-9
    return np.median(hits[clump], axis=0)


BLOB = 0.6  # a preview blob's standard deviation, in grid cells: neighbours just overlap
_AXIS_BITS = 21  # grid indexes per axis that fit side by side in one int64 key


def _cell_keys(positions: np.ndarray, low: np.ndarray, cell: float) -> np.ndarray:
    index = np.floor((positions - low) / cell).astype(np.int64)
    np.clip(index, 0, (1 << _AXIS_BITS) - 1, out=index)
    return (index[:, 0] << (2 * _AXIS_BITS)) | (index[:, 1] << _AXIS_BITS) | index[:, 2]


def thin(
    positions: np.ndarray, opacities: np.ndarray, colors: np.ndarray, target: int
) -> dict[str, np.ndarray] | None:
    """A coarse copy of a scene in about `target` Gaussians, or None when it already has fewer.

    The scene is cut into a grid and every occupied cell becomes one round blob: at the
    opacity-weighted middle of the cell's Gaussians, in their mean colour, as wide as the cell.
    Surfaces stay covered at any size, which keeping "the best N" does not do (that keeps the
    big background smears and leaves holes). The cell size is found in two passes: surfaces
    fill cells in proportion to 1 / cell^2.
    """
    count = len(positions)
    if count <= target:
        return None
    low = positions.min(axis=0)
    sample = positions[:: max(1, count // 20_000)]
    span = np.maximum(np.quantile(sample, 0.98, axis=0) - np.quantile(sample, 0.02, axis=0), 1e-6)
    area = 2 * (span[0] * span[1] + span[1] * span[2] + span[0] * span[2])
    cell = float(np.sqrt(area / target))
    occupied = len(np.unique(_cell_keys(positions, low, cell)))
    cell *= float(np.sqrt(occupied / target))
    _, inverse = np.unique(_cell_keys(positions, low, cell), return_inverse=True)
    cells = int(inverse.max()) + 1

    weight = np.asarray(opacities, dtype=np.float64)
    total = np.maximum(np.bincount(inverse, weights=weight, minlength=cells), 1e-12)

    def mean(values: np.ndarray) -> np.ndarray:
        return np.stack(
            [
                np.bincount(inverse, weights=weight * values[:, k], minlength=cells) / total
                for k in range(3)
            ],
            axis=1,
        )

    rotations = np.zeros((cells, 4), dtype=np.float32)
    rotations[:, 3] = 1.0
    return {
        "positions": mean(positions).astype(np.float32),
        "scales": np.full((cells, 3), cell * BLOB, dtype=np.float32),
        "rotations": rotations,
        "opacities": np.minimum(total, 0.98).astype(np.float32),
        "colors": mean(colors).astype(np.float32),
    }


def importance(scales: np.ndarray, opacities: np.ndarray) -> np.ndarray:
    """How much one Gaussian adds to the picture: its opacity times the area of its two larger
    axes. The preview keeps the highest."""
    scales = np.asarray(scales)
    smallest = np.maximum(scales.min(axis=1), 1e-12)
    return np.asarray(opacities) * scales.prod(axis=1) / smallest
