"""The replay script's frame cutting and timestamp rebasing."""

import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from PIL import Image

from scripts.replay_video import capture_times, extract_frames

START = datetime(2026, 11, 15, 1, 0, tzinfo=UTC)


def test_capture_times_keep_video_spacing_and_end_when_the_last_frame_is_sent() -> None:
    stamps = capture_times(4, interval=0.5, speed=1.0, start=START)

    assert stamps[-1] == START + timedelta(seconds=1.5)
    assert [(b - a).total_seconds() for a, b in zip(stamps, stamps[1:], strict=False)] == [0.5] * 3


def test_a_faster_replay_still_spaces_frames_by_video_time() -> None:
    stamps = capture_times(3, interval=2.0, speed=4.0, start=START)

    assert stamps[-1] == START + timedelta(seconds=1.0)  # 4 s of video sent in 1 s
    assert stamps[0] == START - timedelta(seconds=3.0)  # every stamp is in the past when sent


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_extract_frames_cuts_one_upright_jpeg_per_interval(tmp_path: Path) -> None:
    plain, video = tmp_path / "plain.mp4", tmp_path / "walk.mp4"
    ffmpeg = ["ffmpeg", "-v", "error"]
    subprocess.run(
        [*ffmpeg, "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=3",
         "-pix_fmt", "yuv420p", str(plain)],
        check=True,
    )  # fmt: skip
    # A phone held upright stores landscape pixels plus a rotation flag, as IMG_2092.MOV does.
    subprocess.run(
        [*ffmpeg, "-display_rotation", "90", "-i", str(plain), "-c", "copy", str(video)],
        check=True,
    )
    out = tmp_path / "frames"
    out.mkdir()

    frames = extract_frames(video, 0.5, out)

    assert len(frames) == 6
    with Image.open(frames[0]) as image:
        assert image.format == "JPEG"
        assert image.size == (360, 640)  # the rotation flag was applied
