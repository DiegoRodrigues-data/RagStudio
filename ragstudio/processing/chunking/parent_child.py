"""Parent-child chunking: small child chunks are indexed; each one knows the span of its larger parent.

`size` / `overlap` describe the children; `parent_size` the parents (no overlap between parents). The technique
`parent_child` retrieves children and sends the parents to the context.
"""
from __future__ import annotations

from typing import Any

from .fixed import windows


def spans(text: str, size: int = 300, overlap: int = 50, parent_size: int = 1500,
          **_: Any) -> list[tuple[int, int, dict[str, Any]]]:
    out: list[tuple[int, int, dict[str, Any]]] = []
    parents = windows(text, 0, len(text), max(int(parent_size), int(size)), 0)
    for n, (p_start, p_end) in enumerate(parents):
        for s, e in windows(text, p_start, p_end, int(size), int(overlap)):
            out.append((s, e, {"parent": n, "parent_start": p_start, "parent_end": p_end}))
    return out
