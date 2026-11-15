"""Build the room's 3D scan from a video or a folder of photos, for `GET /room`.

    uv run python -m scripts.build_room ~/Downloads/IMG_2101.MOV       # a 20 to 40 s walk
    uv run python -m scripts.build_room photos/ --frames 48            # a folder of photos
    uv run python -m scripts.build_room scan.mov --no-full             # the small preview only

The splat builder must be reachable at SPLAT_URL (default http://127.0.0.1:8900: the SSH tunnel
to the GPU machine, or a local `SPLAT_MODEL=mock python -m splat.server`); see docs/SPLAT.md.

Everything slow happens on the laptop so that little crosses the network: still frames are cut
from the video here (ffmpeg, or AVFoundation on a Mac without it), the sharpest evenly spaced ones
are picked, shrunk to the 448 px squares the model takes and sent in one request (about 50 KB a
frame). The GPU answers when the small preview is ready; it is saved first, then the full file.
The result goes to ROOM_DIR (`.cache/room/`, gitignored): `preview.spz`, `full.spz`, `scene.json`.
A new scan has its own coordinates, so the landmark pins of the previous one are cleared
(`landmarks.x/y/z`); place them again in `/room`.

Staged rooms only: the frames go to a rented GPU, and a scan of a real home is as sensitive as
the frames themselves (D25).
"""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.config import get_settings
from app.memory import db
from splat import frames as frame_tools

REPO = Path(__file__).resolve().parent.parent
SWIFT_SOURCE = REPO / "scripts" / "video_frames.swift"
SWIFT_BINARY = REPO / ".cache" / "bin" / "video_frames"
VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v", ".webm"}
PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png"}
APPLE_SUFFIXES = {".heic", ".heif"}  # Pillow cannot read these; macOS `sips` converts them
CANDIDATES_PER_FRAME = 3  # stills cut per frame sent, so the sharpest of each stretch can win
EXTRACT_SIDE = 896  # twice what the model takes: enough to judge sharpness and shrink cleanly
MAX_CANDIDATES = 400


def _swift_extractor() -> Path:
    """The compiled AVFoundation frame cutter, built once (a Swift script costs 20 s a run)."""
    if SWIFT_BINARY.exists() and SWIFT_BINARY.stat().st_mtime >= SWIFT_SOURCE.stat().st_mtime:
        return SWIFT_BINARY
    SWIFT_BINARY.parent.mkdir(parents=True, exist_ok=True)
    print("compiling the frame cutter (once)...", flush=True)
    subprocess.run(
        ["swiftc", "-O", "-suppress-warnings", str(SWIFT_SOURCE), "-o", str(SWIFT_BINARY)],
        check=True,
    )
    return SWIFT_BINARY


def _duration_s(video: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())


def extract_frames(video: Path, count: int, out: Path) -> list[Path]:
    """`count` evenly spaced upright stills from the video, at most EXTRACT_SIDE px."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        rate = count / max(_duration_s(video), 0.1)
        scale = f"scale='min({EXTRACT_SIDE},iw)':'min({EXTRACT_SIDE},ih)'"
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-i", str(video),
                "-vf", f"fps={rate:.6f},{scale}:force_original_aspect_ratio=decrease",
                "-q:v", "2", str(out / "%05d.jpg"),
            ],
            check=True,
        )  # fmt: skip
    elif sys.platform == "darwin" and shutil.which("swiftc"):
        subprocess.run(
            [str(_swift_extractor()), str(video), str(out), str(count), str(EXTRACT_SIDE)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    else:
        raise SystemExit("cutting frames from a video needs ffmpeg (or a Mac with Xcode's tools)")
    return sorted(out.glob("*.jpg"))


def gather(source: Path, frames: int, tmp: Path) -> list[Path]:
    """The candidate photos, in capture order: stills cut from a video, or a folder's images."""
    if source.is_dir():
        photos = []
        for path in sorted(source.iterdir()):
            suffix = path.suffix.lower()
            if suffix in PHOTO_SUFFIXES:
                photos.append(path)
            elif suffix in APPLE_SUFFIXES and shutil.which("sips"):
                converted = tmp / f"{path.stem}.jpg"
                subprocess.run(
                    ["sips", "-s", "format", "jpeg", str(path), "--out", str(converted)],
                    check=True,
                    capture_output=True,
                )
                photos.append(converted)
        return photos
    if source.suffix.lower() in VIDEO_SUFFIXES:
        return extract_frames(source, min(MAX_CANDIDATES, frames * CANDIDATES_PER_FRAME), tmp)
    raise SystemExit(f"{source} is neither a folder of photos nor a video")


def _score(path: Path) -> float:
    return frame_tools.sharpness(frame_tools.open_upright(path.read_bytes()))


def _shrink(path: Path) -> bytes:
    return frame_tools.to_jpeg(frame_tools.prepare(frame_tools.open_upright(path.read_bytes())))


def choose(photos: list[Path], frames: int) -> tuple[list[bytes], list[int]]:
    """The JPEGs to send (448 px squares, no metadata) and which candidates they are."""
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        scores = list(pool.map(_score, photos))
        chosen = frame_tools.pick(scores, frames)
        return list(pool.map(_shrink, [photos[i] for i in chosen])), chosen


async def _clear_pins() -> int:
    """A new scan has new coordinates, so every landmark pin of the old one is wrong now."""
    placed = [pin for pin in await db.list_pins() if pin.position is not None]
    for pin in placed:
        await db.set_pin(pin.landmark_id, None)
    return len(placed)


def _save(folder: Path, name: str, data: bytes) -> None:
    """Whole file or nothing: the backend may be serving the old one right now."""
    partial = folder / f".{name}.part"
    partial.write_bytes(data)
    partial.replace(folder / name)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("source", type=Path, help="a video, or a folder of photos")
    parser.add_argument("--frames", type=int, default=32, help="photos the model gets (2 to 128)")
    parser.add_argument("--url", default=settings.splat_url)
    parser.add_argument("--out", type=Path, default=settings.room_dir)
    parser.add_argument("--preview", type=int, default=100_000, help="Gaussians in the preview")
    parser.add_argument("--full", type=int, default=1_000_000, help="in the full file; 0 for all")
    parser.add_argument("--no-full", action="store_true", help="stop after the preview")
    args = parser.parse_args()
    if not 2 <= args.frames <= 128:
        parser.error("--frames must be 2 to 128")
    if not args.source.exists():
        parser.error(f"{args.source} does not exist")
    headers = {}
    if settings.splat_token is not None:
        headers["Authorization"] = f"Bearer {settings.splat_token.get_secret_value()}"

    started = time.perf_counter()
    marks: dict[str, float] = {}

    def mark(stage: str, since: float) -> float:
        now = time.perf_counter()
        marks[stage] = round(now - since, 2)
        return now

    with (
        tempfile.TemporaryDirectory(prefix="room-") as tmp,
        httpx.Client(
            base_url=args.url, headers=headers, timeout=httpx.Timeout(600, connect=10)
        ) as http,
    ):
        try:
            # Its own connection: cutting frames can take longer than the server keeps one open.
            health = http.get("/health", timeout=10, headers={"Connection": "close"}).json()
        except httpx.HTTPError as exc:
            raise SystemExit(f"no splat builder at {args.url} ({exc}); see docs/SPLAT.md") from exc
        print(f"builder: {health.get('model')} on {health.get('gpu_name') or 'no GPU'}")

        photos = gather(args.source, args.frames, Path(tmp))
        if len(photos) < 2:
            raise SystemExit(f"need at least 2 photos, found {len(photos)} in {args.source}")
        at = mark("frames_cut", started)
        jpegs, chosen = choose(photos, args.frames)
        at = mark("frames_chosen", at)
        size = sum(len(j) for j in jpegs)
        print(f"{len(photos)} candidate photos, sending {len(jpegs)} ({size / 1024:.0f} KB)")

        response = http.post(
            "/build",
            params={
                "max_frames": args.frames,
                "preview_gaussians": args.preview,
                "full_gaussians": args.full,
            },
            files=[
                ("frames", (f"{i:05d}.jpg", jpeg, "image/jpeg")) for i, jpeg in enumerate(jpegs)
            ],
        )
        response.raise_for_status()
        scene = response.json()
        at = mark("upload_and_build", at)
        if scene["status"] == "failed":
            raise SystemExit(f"the build failed: {scene['error']}")
        scene_id = scene["scene_id"]

        args.out.mkdir(parents=True, exist_ok=True)
        built_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        preview = http.get(f"/scenes/{scene_id}/splat", params={"level": "preview"})
        preview.raise_for_status()
        cameras = http.get(f"/scenes/{scene_id}/cameras")
        cameras.raise_for_status()
        description = {
            **cameras.json(),
            "scene_id": scene_id,
            "source": args.source.name,
            "built_at": built_at,
            "levels": ["preview"],
        }
        (args.out / "full.spz").unlink(missing_ok=True)  # never show an older room's full file
        _save(args.out, "preview.spz", preview.content)
        _save(args.out, "scene.json", json.dumps(description).encode())
        at = mark("preview_download", at)
        marks["to_preview"] = round(at - started, 2)
        if args.out.resolve() == settings.room_dir.resolve():  # a side build keeps the pins
            try:
                cleared = asyncio.run(_clear_pins())
                if cleared:
                    print(f"cleared {cleared} pins of the previous scan: place them again in /room")
            except Exception as exc:  # the room is still built; say so and carry on
                print(f"could not clear the old pins ({type(exc).__name__}): place them again")
        print(
            f"preview ready after {marks['to_preview']} s: "
            f"{scene['gaussians']['preview']:,} Gaussians, {len(preview.content) / 1e6:.1f} MB"
        )

        if not args.no_full:
            while scene["status"] not in ("ready", "failed"):
                time.sleep(0.2)
                scene = http.get(f"/scenes/{scene_id}").json()
            if scene["status"] == "failed":
                raise SystemExit(f"the full build failed: {scene['error']}")
            full = http.get(f"/scenes/{scene_id}/splat", params={"level": "full"})
            full.raise_for_status()
            description = {**description, **http.get(f"/scenes/{scene_id}/cameras").json()}
            description["levels"] = ["preview", "full"]
            _save(args.out, "full.spz", full.content)
            at = mark("full_download", at)
            print(
                f"full file: {scene['gaussians']['full']:,} Gaussians, "
                f"{len(full.content) / 1e6:.1f} MB"
            )
        description["client_timings_s"] = {**marks, "total": round(at - started, 2)}
        _save(args.out, "scene.json", json.dumps(description).encode())
        http.delete(f"/scenes/{scene_id}")  # nothing of the room stays on the GPU machine

    gpu = description.get("timings_ms", {})
    print(
        "laptop, seconds: "
        + "  ".join(f"{k}={v}" for k, v in description["client_timings_s"].items())
    )
    print("GPU, milliseconds: " + "  ".join(f"{k}={v:.0f}" for k, v in gpu.items()))
    print(f"saved to {args.out}; open http://localhost:8000/room")


if __name__ == "__main__":
    main()
