"""Recursive chunking: split at the largest natural boundary that makes the pieces fit, then pack them.

The text is cut at paragraph breaks first; a piece still larger than `size` is cut at line breaks, then at
sentence ends, then at spaces, and only as a last resort at a fixed width. Neighbouring pieces are packed back
together up to `size`, with trailing pieces repeated as overlap. This is the idea of LangChain's
RecursiveCharacterTextSplitter, written over offsets so every chunk stays an exact slice of the document.
"""
from __future__ import annotations

from typing import Any

SEPARATORS = ("\n\n", "\n", ". ", "; ", ", ", " ")


def pieces(text: str, start: int, end: int, size: int, separators: tuple[str, ...] = SEPARATORS) -> list[tuple[int, int]]:
    """Contiguous spans covering text[start:end], each at most `size` long (a separator stays with its left piece)."""
    if end - start <= size:
        return [(start, end)]
    for position, separator in enumerate(separators):
        cuts, cursor = [], start
        while (found := text.find(separator, cursor, end)) != -1:
            cursor = found + len(separator)
            if cursor < end:
                cuts.append(cursor)
        if cuts:
            bounds = [start, *cuts, end]
            out: list[tuple[int, int]] = []
            for a, b in zip(bounds, bounds[1:], strict=False):
                out.extend(pieces(text, a, b, size, separators[position + 1:]))
            return out
    return [(a, min(a + size, end)) for a in range(start, end, size)]


def spans(text: str, size: int = 1000, overlap: int = 150, **_: Any) -> list[tuple[int, int, dict[str, Any]]]:
    size, overlap = int(size), int(overlap)
    parts = pieces(text, 0, len(text), size)
    out: list[tuple[int, int, dict[str, Any]]] = []
    i = 0
    while i < len(parts):
        j = i
        while j + 1 < len(parts) and parts[j + 1][1] - parts[i][0] <= size:
            j += 1
        out.append((parts[i][0], parts[j][1], {"pieces": j - i + 1}))
        if j + 1 >= len(parts):
            break
        nxt = j + 1
        while nxt > i + 1 and parts[j][1] - parts[nxt - 1][0] <= overlap:
            nxt -= 1
        i = nxt
    return out
