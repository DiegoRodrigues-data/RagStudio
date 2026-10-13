"""One chunk per Markdown section; long sections fall back to fixed windows. Heading path kept as metadata."""
from __future__ import annotations

import re
from typing import Any

from .fixed import windows

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)


def spans(text: str, size: int = 1000, overlap: int = 150, **_: Any) -> list[tuple[int, int, dict[str, Any]]]:
    marks = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in _HEADING.finditer(text)]
    bounds = [0] + [pos for pos, _, _ in marks if pos > 0] + [len(text)]
    bounds = sorted(set(bounds))
    out: list[tuple[int, int, dict[str, Any]]] = []
    path: list[tuple[int, str]] = []
    by_pos = {pos: (level, title) for pos, level, title in marks}
    for start, end in zip(bounds, bounds[1:], strict=False):
        if start in by_pos:
            level, title = by_pos[start]
            path = [(lv, t) for lv, t in path if lv < level] + [(level, title)]
        meta = {"headings": [t for _, t in path]}
        for s, e in windows(text, start, end, int(size), int(overlap)):
            out.append((s, e, dict(meta)))
    return out
