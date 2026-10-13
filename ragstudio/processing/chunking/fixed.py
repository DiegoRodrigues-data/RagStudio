"""Fixed-size windows with overlap, cut at whitespace when possible. Ported from `ragkit/chunking.py`."""
from __future__ import annotations

from typing import Any


def windows(text: str, begin: int, finish: int, size: int, overlap: int) -> list[tuple[int, int]]:
    """Windows covering text[begin:finish]; each ends at the last whitespace within the final 20% of the window."""
    out: list[tuple[int, int]] = []
    start = begin
    while start < finish:
        end = min(start + size, finish)
        if end < finish:
            cut = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            if cut > start + int(size * 0.8):
                end = cut
        out.append((start, end))
        if end >= finish:
            break
        start = max(end - overlap, start + 1)
    return out


def spans(text: str, size: int = 1000, overlap: int = 150, **_: Any) -> list[tuple[int, int, dict[str, Any]]]:
    return [(s, e, {}) for s, e in windows(text, 0, len(text), int(size), int(overlap))]
