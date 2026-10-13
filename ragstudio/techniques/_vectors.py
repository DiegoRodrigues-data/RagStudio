"""Small vector helpers shared by techniques that embed their own structures (graph nodes, tree summaries)."""
from __future__ import annotations

import numpy as np

from ..core.contract import TechniqueDeps

_VECTORS: dict[tuple[str, str, str, int], np.ndarray] = {}


def unit_rows(vectors: list[list[float]]) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.size == 0:
        return matrix.reshape(0, 0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1.0, norms)


def vectors(deps: TechniqueDeps, key: str, kind: str, texts: list[str]) -> np.ndarray:
    """Row-normalized embeddings of `texts`, memoized per index, graph and kind for this process."""
    memo = (deps.store.meta.index_hash, key, kind, len(texts))
    if memo not in _VECTORS:
        _VECTORS[memo] = unit_rows(deps.embed(texts) if texts else [])
    return _VECTORS[memo]


def similarities(matrix: np.ndarray, query_vector: list[float]) -> np.ndarray:
    if matrix.size == 0:
        return np.zeros(0, dtype=np.float32)
    query = np.asarray(query_vector, dtype=np.float32)
    with np.errstate(all="ignore"):
        return matrix @ (query / (np.linalg.norm(query) or 1.0))


def top(scores: np.ndarray, limit: int, minimum: float = 0.0) -> list[tuple[int, float]]:
    order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))[:limit]
    return [(i, float(scores[i])) for i in order if float(scores[i]) > minimum]
