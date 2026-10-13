"""Markdown cleaning. Each flag is independent and the applied flags are recorded with the corpus.

Ported from the JudDoc_Ex cleaner (`remove_image_tags`, `remove_repeated_headers`, `collapse_blank_lines`,
`remove_print_metadata`).
"""
from __future__ import annotations

import re
from collections import Counter

FLAGS = ("remove_image_tags", "remove_repeated_headers", "collapse_blank_lines", "remove_print_metadata")

_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<!--\s*image\s*-->", re.I)
_PRINT = re.compile(r"^\s*(p[áa]gina|page)\s+\d+(\s+(de|of)\s+\d+)?\s*$|^\s*\d+\s*/\s*\d+\s*$", re.I)


def clean(text: str, flags: list[str] | tuple[str, ...] = FLAGS) -> str:
    unknown = set(flags) - set(FLAGS)
    if unknown:
        raise ValueError(f"unknown cleaning flags: {sorted(unknown)}")
    if "remove_image_tags" in flags:
        text = _IMAGE.sub("", text)
    lines = text.split("\n")
    if "remove_print_metadata" in flags:
        lines = [line for line in lines if not _PRINT.match(line)]
    if "remove_repeated_headers" in flags:
        counts = Counter(line.strip() for line in lines if 0 < len(line.strip()) <= 80)
        repeated = {line for line, n in counts.items() if n >= 4 and not line.startswith(("-", "*", "|", "#"))}
        seen: set[str] = set()
        kept = []
        for line in lines:
            key = line.strip()
            if key in repeated:
                if key in seen:
                    continue
                seen.add(key)
            kept.append(line)
        lines = kept
    text = "\n".join(lines)
    if "collapse_blank_lines" in flags:
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
