#!/usr/bin/env python3
"""Generate a line-level LRC file by aligning a lyrics text file to audio.

Usage:
    python scripts/align_lrc.py assets/song.mp3 lyrics.txt -o song.lrc
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\u2019][A-Za-z0-9]+)?")


@dataclass
class LyricLine:
    text: str
    word_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Forced-align a line-broken lyrics.txt file to audio and save .lrc."
    )
    parser.add_argument("audio", type=Path, help="Path to input audio file (.mp3/.wav/etc).")
    parser.add_argument("lyrics", type=Path, help="Path to line-broken lyrics text file.")
    parser.add_argument("-o", "--output", type=Path, help="Output .lrc path.")
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model for stable-ts alignment: tiny, base, small, medium, large. Default: base.",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code passed to stable-ts alignment. Default: en.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Device for Whisper model, e.g. cpu or cuda. Default: stable-ts auto.",
    )
    parser.add_argument(
        "--keep-empty-lines",
        action="store_true",
        help="Keep empty lines in output if present in the input text.",
    )
    parser.add_argument(
        "--preview-lines",
        type=int,
        default=10,
        help="Print the first N generated LRC lines. Default: 10.",
    )
    parser.add_argument(
        "--json-debug",
        type=Path,
        help="Optional path to save word-level alignment JSON for debugging.",
    )
    return parser.parse_args()


def normalize_text_line(line: str) -> str:
    return " ".join(line.strip().split())


def count_words(line: str) -> int:
    return len(WORD_RE.findall(line))


def read_lyrics(path: Path, keep_empty: bool) -> list[LyricLine]:
    raw_lines = path.read_text(encoding="utf-8-sig").splitlines()
    lines: list[LyricLine] = []

    for raw_line in raw_lines:
      text = normalize_text_line(raw_line)
      if not text and not keep_empty:
          continue
      lines.append(LyricLine(text=text, word_count=count_words(text)))

    if not lines:
        raise ValueError(f"No lyric lines found in {path}")

    if sum(line.word_count for line in lines) == 0:
        raise ValueError("Lyrics file contains no alignable words.")

    return lines


def flatten_result_words(result) -> list[dict]:
    words: list[dict] = []

    for segment in getattr(result, "segments", []):
        for word in getattr(segment, "words", []) or []:
            word_text = getattr(word, "word", None)
            start = getattr(word, "start", None)
            end = getattr(word, "end", None)
            if word_text is None and isinstance(word, dict):
                word_text = word.get("word")
                start = word.get("start")
                end = word.get("end")
            if word_text is None or start is None:
                continue
            words.append({"word": str(word_text).strip(), "start": float(start), "end": float(end or start)})

    if not words:
        raise ValueError("Alignment produced no word timestamps.")

    return words


def get_obj_value(item, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def extract_segment_starts(result, expected_count: int) -> list[float] | None:
    segments = list(getattr(result, "segments", []) or [])
    if len(segments) != expected_count:
        return None

    starts: list[float] = []
    for segment in segments:
        words = list(get_obj_value(segment, "words", []) or [])
        if words:
            starts.append(float(get_obj_value(words[0], "start", get_obj_value(segment, "start", 0.0))))
            continue
        starts.append(float(get_obj_value(segment, "start", 0.0)))

    return starts


def format_lrc_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes:02d}:{remainder:05.2f}"


def build_lrc(
    lines: list[LyricLine],
    words: list[dict],
    segment_starts: list[float] | None = None,
) -> list[str]:
    lrc_lines: list[str] = []
    word_index = 0
    last_time = 0.0
    non_empty_line_index = 0

    for line in lines:
        if line.word_count == 0:
            timestamp = last_time
        elif segment_starts is not None:
            timestamp = segment_starts[non_empty_line_index]
            last_time = timestamp
            non_empty_line_index += 1
        elif word_index < len(words):
            timestamp = words[word_index]["start"]
            last_time = timestamp
        else:
            timestamp = last_time

        lrc_lines.append(f"[{format_lrc_time(timestamp)}]{line.text}")
        if line.word_count:
            word_index += line.word_count

    if segment_starts is None:
        if word_index > len(words):
            missing = word_index - len(words)
            print(
                f"Warning: lyrics expected {word_index} words, but alignment returned {len(words)} words "
                f"({missing} missing at the end).",
                file=sys.stderr,
            )
        elif len(words) - word_index > 3:
            print(
                f"Warning: alignment returned {len(words) - word_index} extra words after mapping lyrics lines.",
                file=sys.stderr,
            )

    return lrc_lines


def write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    if not args.audio.exists():
        raise FileNotFoundError(args.audio)
    if not args.lyrics.exists():
        raise FileNotFoundError(args.lyrics)

    output = args.output or args.audio.with_suffix(".lrc")
    lines = read_lyrics(args.lyrics, keep_empty=args.keep_empty_lines)
    plain_text = "\n".join(line.text for line in lines if line.text)

    import stable_whisper

    print(f"Loading stable-ts Whisper model: {args.model}")
    model = stable_whisper.load_model(args.model, device=args.device)

    print(f"Aligning {args.audio} to {args.lyrics}")
    result = model.align(
        str(args.audio),
        plain_text,
        language=args.language,
        original_split=True,
    )
    if result is None:
        raise RuntimeError("stable-ts alignment failed and returned no result.")

    words = flatten_result_words(result)
    alignable_line_count = sum(1 for line in lines if line.word_count)
    segment_starts = extract_segment_starts(result, alignable_line_count)
    if segment_starts is None:
        print("Warning: stable-ts did not return one segment per lyric line; using word-count fallback.", file=sys.stderr)
    lrc_lines = build_lrc(lines, words, segment_starts=segment_starts)
    write_lines(output, lrc_lines)

    if args.json_debug:
        args.json_debug.parent.mkdir(parents=True, exist_ok=True)
        args.json_debug.write_text(json.dumps(words, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {output}")
    print(f"Mapped {len(lines)} lyric lines using {len(words)} word timestamps.")
    print("\nPreview:")
    for line in lrc_lines[: max(0, args.preview_lines)]:
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
