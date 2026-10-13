"""Maximal Marginal Relevance (Carbonell & Goldstein, SIGIR 1998). Ported from `ragkit/mmr.py`.

    MMR = argmax_d [ lambda * sim(d, q) - (1 - lambda) * max_{s in selected} sim(d, s) ]

lambda_ = 1 is pure relevance (same order as dense); lambda_ = 0 is pure diversity after the first pick.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..core.models import RetrievedChunk
from ..stores.base import IndexStore
from . import dense


def mmr_select(query_vector: list[float], doc_vectors: list[list[float]], k: int, lambda_: float = 0.5) -> list[int]:
    if not doc_vectors:
        return []
    docs = np.asarray(doc_vectors, dtype=np.float64)
    docs = docs / np.where(np.linalg.norm(docs, axis=1, keepdims=True) == 0, 1.0,
                           np.linalg.norm(docs, axis=1, keepdims=True))
    query = np.asarray(query_vector, dtype=np.float64)
    query = query / (np.linalg.norm(query) or 1.0)
    with np.errstate(all="ignore"):  # numpy/Accelerate emits spurious matmul warnings on macOS arm64
        relevance = docs @ query
        similarity = docs @ docs.T
    selected: list[int] = []
    remaining = list(range(len(doc_vectors)))
    while remaining and len(selected) < k:
        if not selected:
            best = max(remaining, key=lambda i: (relevance[i], -i))
        else:
            best = max(remaining, key=lambda i: (lambda_ * relevance[i]
                                                 - (1 - lambda_) * float(similarity[i, selected].max()), -i))
        selected.append(best)
        remaining.remove(best)
    return selected


def search(store: IndexStore, query_vector: list[float], k: int, filters: dict[str, Any] | None = None,
           lambda_: float = 0.6, k_candidates: int = 40) -> list[RetrievedChunk]:
    candidates = dense.search(store, query_vector, max(k_candidates, k), filters)
    vectors = [store.embedding(c.chunk.id) for c in candidates]
    picked = mmr_select(query_vector, vectors, k, lambda_)
    return [RetrievedChunk(candidates[i].chunk, candidates[i].score, rank, "mmr") for rank, i in enumerate(picked, 1)]
