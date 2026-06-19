#!/usr/bin/env python3
"""Clean copied Genius-style markdown into line-broken lyrics text.

The script removes section headers, ads/recommendations, markdown links, and
non-sung bracket-only notes. It does not contain any lyrics itself.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
SECTION_RE = re.compile(
    r"^\[[^\]]*(?:"
    r"text|lyrics|verse|chorus|pre-chorus|bridge|intro|interlude|outro|"
    r"текст песни|куплет|припев|предприпев|бридж|интро|интерлюдия|аутро"
    r")[^\]]*\]$",
    re.IGNORECASE,
)
BRACKET_NOTE_RE = re.compile(r"^\[+([^][]+)\]+$")
SKIP_EXACT = {
    "You might also like",
}
SKIP_PREFIXES = (
    "Get tickets as low as",
)
SKIP_BRACKET_NOTES = {
    "guitar solo",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean Genius-style markdown lyrics into plain line text.")
    parser.add_argument("input", type=Path, help="Raw copied markdown/text file.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Clean line-broken lyrics text file.")
    return parser.parse_args()


def strip_markdown_links(line: str) -> str:
    previous = None
    current = line
    while previous != current:
        previous = current
        current = MARKDOWN_LINK_RE.sub(r"\1", current)
    return current


def clean_line(line: str) -> str:
    line = strip_markdown_links(line)
    line = line.replace("\\]", "]").replace("\\[", "[")
    return " ".join(line.strip().split())


def is_section_or_note(line: str) -> bool:
    if SECTION_RE.match(line):
        return True

    note_match = BRACKET_NOTE_RE.match(line)
    if not note_match:
        return False

    note = note_match.group(1).strip().lower()
    return note in SKIP_BRACKET_NOTES or ":" in note


def should_skip(line: str, skipping_recommendations: bool) -> tuple[bool, bool]:
    if not line:
        return True, skipping_recommendations

    if is_section_or_note(line):
        return True, False

    if line in SKIP_EXACT:
        return True, line == "You might also like"

    if any(line.startswith(prefix) for prefix in SKIP_PREFIXES):
        return True, skipping_recommendations

    if skipping_recommendations:
        return True, skipping_recommendations

    return False, skipping_recommendations


def main() -> int:
    args = parse_args()
    raw_lines = args.input.read_text(encoding="utf-8-sig").splitlines()
    output_lines: list[str] = []
    skipping_recommendations = False

    for raw_line in raw_lines:
        line = clean_line(raw_line)
        skip, skipping_recommendations = should_skip(line, skipping_recommendations)
        if skip:
            continue
        output_lines.append(line)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(output_lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
