"""Write (and read back) `.spz`, Niantic's compressed Gaussian splat file. numpy only.

Why not PLY: one Gaussian is 68 bytes in a PLY and about 9 to 11 here after gzip, and writing it
straight from the model's arrays skips a PLY export and a converter subprocess. Spark, the viewer
library, reads `.spz` directly.

The layout follows the reference encoder (github.com/nianticlabs/spz, `src/cc/load-spz.cc`,
read 15 Nov 2026). We write the gzip container, versions 2 and 3; version 4 (zstd) is newer than
some readers. One gzip stream holding:

    header, 16 bytes little-endian: magic 0x5053474e, version, point count (uint32 each),
            SH degree, fractional bits, flags, reserved (uint8 each)
    positions  N x 3 x 3 bytes   24-bit signed fixed point, `fractional bits` after the point
    alphas     N bytes           opacity 0..1 as 0..255
    colors     N x 3 bytes       SH band 0 coefficient: c * 0.15 * 255 + 127.5
    scales     N x 3 bytes       (ln(scale) + 10) * 16
    rotations  v2: N x 3 bytes   x, y, z of the unit quaternion with w >= 0: q * 127.5 + 127.5
               v3: N x 4 bytes   "smallest three": index of the largest part (2 bits), then the
                                 other three as sign + 9 bits of |q| / sqrt(1/2), in a uint32

Positions are in SPZ's own axes, which are three.js's: x right, y up, z back (`geometry.py`
converts from the model's). Quaternions are x, y, z, w. Python 3.10 syntax.
"""

from __future__ import annotations

import gzip
import struct

import numpy as np

MAGIC = 0x5053474E
FRACTIONAL_BITS = 12  # 1/4096 of a scene unit; positions reach +-2048 units
COLOR_SCALE = 0.15
SH_C0 = 0.28209479177387814  # band 0 of the spherical harmonics: rgb = 0.5 + SH_C0 * coefficient
_HEADER = struct.Struct("<IIIBBBB")
_SQRT1_2 = float(np.sqrt(0.5))


def _to_uint8(values: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(values), 0, 255).astype(np.uint8)


def _unit(rotations: np.ndarray) -> np.ndarray:
    q = np.asarray(rotations, dtype=np.float64)
    norm = np.linalg.norm(q, axis=1, keepdims=True)
    q = np.divide(q, norm, out=np.zeros_like(q), where=norm > 0)
    q[norm[:, 0] == 0] = (0.0, 0.0, 0.0, 1.0)  # a zero quaternion becomes "no rotation"
    return q


def _pack_first_three(q: np.ndarray) -> np.ndarray:
    q = np.where(q[:, 3:4] < 0, -q, q)
    return _to_uint8(q[:, :3] * 127.5 + 127.5)


def _pack_smallest_three(q: np.ndarray) -> np.ndarray:
    count = len(q)
    largest = np.abs(q).argmax(axis=1)
    negate = q[np.arange(count), largest] < 0
    packed = largest.astype(np.uint32)
    for part in range(4):
        keep = largest != part
        magnitude = (511.0 * (np.abs(q[:, part]) / _SQRT1_2) + 0.5).astype(np.uint32)
        magnitude = np.minimum(magnitude, 511)
        negative = ((q[:, part] < 0) ^ negate).astype(np.uint32)
        packed = np.where(keep, (packed << 10) | (negative << 9) | magnitude, packed)
    return packed.astype("<u4").view(np.uint8).reshape(count, 4)


def encode(
    positions: np.ndarray,
    scales: np.ndarray,
    rotations: np.ndarray,
    opacities: np.ndarray,
    colors: np.ndarray,
    *,
    version: int = 3,
    compresslevel: int = 6,
) -> bytes:
    """One `.spz` file.

    positions  (N, 3) in viewer axes
    scales     (N, 3) standard deviations, greater than 0 (not logs)
    rotations  (N, 4) quaternions as x, y, z, w
    opacities  (N,)   0..1
    colors     (N, 3) SH band 0 coefficients (`rgb_to_sh0` turns plain 0..1 colours into them)
    """
    if version not in (2, 3):
        raise ValueError("version must be 2 or 3")
    positions = np.asarray(positions)
    count = len(positions)
    for name, array, width in (
        ("positions", positions, 3),
        ("scales", scales, 3),
        ("rotations", rotations, 4),
        ("colors", colors, 3),
    ):
        if np.shape(array) != (count, width):
            raise ValueError(f"{name} must be ({count}, {width}), got {np.shape(array)}")
    if np.shape(opacities) != (count,):
        raise ValueError(f"opacities must be ({count},), got {np.shape(opacities)}")

    fixed = np.rint(positions * (1 << FRACTIONAL_BITS)).astype(np.int64)
    limit = (1 << 23) - 1
    fixed = np.clip(fixed, -limit - 1, limit).astype("<i4")
    position_bytes = fixed.view(np.uint8).reshape(count, 3, 4)[:, :, :3]

    with np.errstate(divide="ignore"):
        log_scales = np.log(np.maximum(np.asarray(scales, dtype=np.float64), 1e-12))
    q = _unit(rotations)
    body = b"".join(
        (
            _HEADER.pack(MAGIC, version, count, 0, FRACTIONAL_BITS, 0, 0),
            position_bytes.tobytes(),
            _to_uint8(np.asarray(opacities, dtype=np.float64) * 255.0).tobytes(),
            _to_uint8(
                np.asarray(colors, dtype=np.float64) * (COLOR_SCALE * 255.0) + 127.5
            ).tobytes(),
            _to_uint8((log_scales + 10.0) * 16.0).tobytes(),
            (_pack_smallest_three(q) if version == 3 else _pack_first_three(q)).tobytes(),
        )
    )
    return gzip.compress(body, compresslevel=compresslevel, mtime=0)


def decode(data: bytes) -> dict[str, np.ndarray]:
    """The arrays of a version 2 or 3 `.spz` without spherical harmonics, as `encode` takes them.
    For tests and for reading point positions back on the laptop."""
    body = gzip.decompress(data)
    magic, version, count, sh_degree, fractional_bits, _flags, _reserved = _HEADER.unpack_from(body)
    if magic != MAGIC:
        raise ValueError("not an .spz file")
    if version not in (2, 3):
        raise ValueError(f"unsupported .spz version {version}")
    offset = _HEADER.size

    def take(size: int) -> np.ndarray:
        nonlocal offset
        piece = np.frombuffer(body, dtype=np.uint8, count=size, offset=offset)
        offset += size
        return piece

    raw = take(count * 9).reshape(count, 3, 3).astype(np.int32)
    fixed = raw[:, :, 0] | (raw[:, :, 1] << 8) | (raw[:, :, 2] << 16)
    fixed = np.where(fixed & 0x800000, fixed - (1 << 24), fixed)
    positions = fixed / float(1 << fractional_bits)
    opacities = take(count) / 255.0
    colors = (take(count * 3).reshape(count, 3) / 255.0 - 0.5) / COLOR_SCALE
    scales = np.exp(take(count * 3).reshape(count, 3) / 16.0 - 10.0)
    if version == 3:
        packed = take(count * 4).view("<u4").astype(np.uint32)
        rotations = np.zeros((count, 4))
        largest = (packed >> 30).astype(np.int64)
        rest = packed.copy()
        total = np.zeros(count)
        for part in (3, 2, 1, 0):
            keep = largest != part
            magnitude = (rest & 511).astype(np.float64) / 511.0 * _SQRT1_2
            value = np.where((rest >> 9) & 1, -magnitude, magnitude)
            rotations[:, part] = np.where(keep, value, 0.0)
            total += np.where(keep, value * value, 0.0)
            rest = np.where(keep, rest >> 10, rest)
        rotations[np.arange(count), largest] = np.sqrt(np.maximum(0.0, 1.0 - total))
    else:
        xyz = take(count * 3).reshape(count, 3) / 127.5 - 1.0
        w = np.sqrt(np.maximum(0.0, 1.0 - (xyz * xyz).sum(axis=1)))
        rotations = np.concatenate([xyz, w[:, None]], axis=1)
    return {
        "positions": positions,
        "scales": scales,
        "rotations": rotations,
        "opacities": opacities,
        "colors": colors,
        "sh_degree": np.asarray(sh_degree),
    }


def count_of(data: bytes) -> int:
    """How many Gaussians a file holds, reading only its first block."""
    with gzip.GzipFile(fileobj=__import__("io").BytesIO(data)) as stream:
        _magic, _version, count, *_ = _HEADER.unpack(stream.read(_HEADER.size))
    return count


def rgb_to_sh0(rgb: np.ndarray) -> np.ndarray:
    return (np.asarray(rgb, dtype=np.float64) - 0.5) / SH_C0


def sh0_to_rgb(colors: np.ndarray) -> np.ndarray:
    return np.clip(0.5 + SH_C0 * np.asarray(colors, dtype=np.float64), 0.0, 1.0)
