"""Sentence-aligned chunks: whole sentences packed up to `size` characters, overlapping by trailing sentences."""
from __future__ import annotations

import re
from typing import Any

_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def sentence_spans(text: str) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start = 0
    for match in _BOUNDARY.finditer(text):
        if text[start:match.start()].strip():
            out.append((start, match.start()))
        start = match.end()
    if text[start:].strip():
        out.append((start, len(text)))
    return out


def spans(text: str, size: int = 1000, overlap: int = 150, **_: Any) -> list[tuple[int, int, dict[str, Any]]]:
    size, overlap = int(size), int(overlap)
    sentences = sentence_spans(text)
    out: list[tuple[int, int, dict[str, Any]]] = []
    i = 0
    while i < len(sentences):
        j = i
        while j + 1 < len(sentences) and sentences[j + 1][1] - sentences[i][0] <= size:
            j += 1
        out.append((sentences[i][0], sentences[j][1], {"sentences": j - i + 1}))
        if j + 1 >= len(sentences):
            break
        nxt = j + 1
        while nxt > i + 1 and sentences[j][1] - sentences[nxt - 1][0] <= overlap:
            nxt -= 1
        i = nxt
    return out
