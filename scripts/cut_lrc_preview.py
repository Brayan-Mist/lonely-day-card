#!/usr/bin/env python3
"""Cut a short audio preview around an LRC timestamp for manual checking."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


LRC_TIME_RE = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\]")


def parse_lrc_time(value: str) -> float:
    match = LRC_TIME_RE.match(value.strip())
    if match:
        return int(match.group(1)) * 60 + float(match.group(2))

    if ":" in value:
        minutes, seconds = value.split(":", 1)
        return int(minutes) * 60 + float(seconds)

    return float(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cut a short clip around an LRC timestamp.")
    parser.add_argument("audio", type=Path, help="Path to the source audio file.")
    parser.add_argument("timestamp", help="Timestamp as seconds, mm:ss.xx, or full [mm:ss.xx]LRC line.")
    parser.add_argument("-o", "--output", type=Path, help="Output clip path. Default: preview_<time>.mp3")
    parser.add_argument("--duration", type=float, default=3.0, help="Clip duration in seconds. Default: 3.")
    parser.add_argument(
        "--pre-roll",
        type=float,
        default=0.35,
        help="Start this many seconds before the timestamp. Default: 0.35.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.audio.exists():
        raise FileNotFoundError(args.audio)

    timestamp = parse_lrc_time(args.timestamp)
    start = max(0.0, timestamp - args.pre_roll)
    safe_label = f"{timestamp:.2f}".replace(".", "_")
    output = args.output or Path(f"preview_{safe_label}.mp3")
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{args.duration:.3f}",
        "-i",
        str(args.audio),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-q:a",
        "2",
        str(output),
    ]
    subprocess.run(command, check=True)
    print(f"Wrote {output} ({start:.2f}s..{start + args.duration:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
