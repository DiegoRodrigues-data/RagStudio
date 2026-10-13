"""Semantic chunking: a chunk ends where the meaning of consecutive sentences changes the most.

Each sentence is embedded together with its neighbours (`buffer` sentences on each side). The cosine distance
between consecutive embeddings is computed, and the positions whose distance is above the `breakpoint_percentile`
of the document become chunk boundaries. A group larger than `size` is packed into sentence-aligned pieces.

It needs an embedder at indexing time and spends embedding tokens on every sentence, on top of the chunk
embeddings. `overlap` is not used: the boundaries are the point of the strategy.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from ...core.errors import ValidationError
from .fixed import windows
from .sentence import sentence_spans

Embed = Callable[[list[str]], list[list[float]]]


def distances(vectors: list[list[float]]) -> np.ndarray:
    """Cosine distance between each sentence window and the next one."""
    matrix = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.where(norms == 0, 1.0, norms)
    return 1.0 - np.einsum("ij,ij->i", matrix[:-1], matrix[1:])


def spans(text: str, size: int = 1000, overlap: int = 0, breakpoint_percentile: float = 90.0, buffer: int = 1,
          embed: Embed | None = None, **_: Any) -> list[tuple[int, int, dict[str, Any]]]:
    if embed is None:
        raise ValidationError("semantic chunking needs an embedder: build the index through `index build` or a runbook")
    size, buffer = int(size), max(0, int(buffer))
    if not 0 < float(breakpoint_percentile) < 100:
        raise ValidationError("breakpoint_percentile must be between 0 and 100")
    sentences = sentence_spans(text)
    if not sentences:
        return []
    breaks: set[int] = set()
    if len(sentences) > 2:
        neighbourhoods = [text[sentences[max(0, i - buffer)][0]:sentences[min(len(sentences) - 1, i + buffer)][1]]
                   for i in range(len(sentences))]
        gaps = distances(embed(neighbourhoods))
        threshold = float(np.percentile(gaps, float(breakpoint_percentile)))
        breaks = {i for i, gap in enumerate(gaps) if gap > threshold}  # a break AFTER sentence i
    out: list[tuple[int, int, dict[str, Any]]] = []
    first = 0
    for i in range(len(sentences)):
        last = i == len(sentences) - 1
        too_long = not last and sentences[i + 1][1] - sentences[first][0] > size
        if last or i in breaks or too_long:
            boundary = "end" if last else "semantic" if i in breaks else "size"
            meta = {"sentences": i - first + 1, "boundary": boundary}
            # one "sentence" longer than the limit (a table, a list without full stops) is cut at fixed width
            out.extend((s, e, dict(meta)) for s, e in windows(text, sentences[first][0], sentences[i][1], size, 0))
            first = i + 1
    return out
