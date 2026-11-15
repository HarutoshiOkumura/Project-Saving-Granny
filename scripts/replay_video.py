"""Replay a recorded walk into `POST /frames` as the lanyard phone would send it.

    uv run python -m scripts.replay_video recordings/walk.mov                 # a frame every 2 s
    uv run python -m scripts.replay_video recordings/walk.mov --interval 0.5  # every 0.5 s
    uv run python -m scripts.replay_video recordings/walk.mov --ask glasses,keys,bag

The API must be running (`uv run uvicorn app.main:app --port 3000`) with APP_TOKEN set; this
script sends the same token from `.env`. ffmpeg cuts one still JPEG per interval (rotation
applied), and the frames go out at the interval, in real time by default, so the server sees what
the phone would send, Gemini's busy slots included. Capture times are rebased so the last frame is
now. With `--ask`, the script waits for the server to finish, then asks `GET /find` per item.
"""

import argparse
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.config import get_settings


def extract_frames(video: Path, interval: float, out: Path) -> list[Path]:
    """One JPEG per `interval` seconds of video, from 0 s, upright, at most 1920 px."""
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(video),
            "-vf",
            f"fps=1/{interval},scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease",
            "-q:v",
            "3",
            str(out / "%05d.jpg"),
        ],
        check=True,
    )
    return sorted(out.glob("*.jpg"))


def capture_times(count: int, interval: float, speed: float, start: datetime) -> list[datetime]:
    """Video time spacing, shifted so the last frame is stamped when it is sent."""
    last_offset = (count - 1) * interval
    last_sent = start + timedelta(seconds=last_offset / speed)
    return [last_sent - timedelta(seconds=last_offset - k * interval) for k in range(count)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("video", type=Path)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between frames (D10)")
    parser.add_argument("--speed", type=float, default=1.0, help="2 sends twice as fast")
    parser.add_argument("--url", default="http://localhost:3000")
    parser.add_argument("--device", help="device id (default: replay-<video name>)")
    parser.add_argument("--ask", default="", help="comma list of items to ask about after")
    parser.add_argument("--settle", type=float, default=20.0, help="seconds to wait before --ask")
    args = parser.parse_args()
    if args.interval <= 0 or args.speed <= 0:
        parser.error("--interval and --speed must be positive")
    token = get_settings().app_token
    if token is None:
        raise SystemExit("APP_TOKEN is not set in .env")
    device = args.device or f"replay-{args.video.stem}"
    headers = {"Authorization": f"Bearer {token.get_secret_value()}"}

    with tempfile.TemporaryDirectory(prefix="replay-") as tmp:
        frames = extract_frames(args.video, args.interval, Path(tmp))
        if not frames:
            raise SystemExit(f"no frames from {args.video}")
        start = datetime.now(UTC)
        stamps = capture_times(len(frames), args.interval, args.speed, start)
        print(
            f"{len(frames)} frames, one per {args.interval} s, device {device}, "
            f"about {(len(frames) - 1) * args.interval / args.speed:.0f} s to send",
            file=sys.stderr,
        )
        clock = time.monotonic()
        with httpx.Client(base_url=args.url, headers=headers, timeout=10) as client:
            for k, (path, stamp) in enumerate(zip(frames, stamps, strict=True)):
                wait = clock + k * args.interval / args.speed - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                response = client.post(
                    "/frames",
                    files={"frame": (path.name, path.read_bytes(), "image/jpeg")},
                    data={"device_id": device, "captured_at": stamp.isoformat()},
                )
                if response.status_code != 202:
                    raise SystemExit(f"frame {k}: HTTP {response.status_code} {response.text}")
            items = [i.strip() for i in args.ask.split(",") if i.strip()]
            if items:
                print(f"waiting {args.settle:.0f} s for the server to finish", file=sys.stderr)
                time.sleep(args.settle)
                for item in items:
                    answer = client.get("/find", params={"item": item, "channel": "web"}).json()
                    print(f"{item}: {answer['sentence']}")


if __name__ == "__main__":
    main()
