"""Hybrid retrieval by weighted sum of max-normalized dense and BM25 scores.

Ported from `ragkit.make_duckdb_hybrid_retriever` (alpha) and JudDoc_Ex `retrieve(mode="hybrid")` (dense_weight).
"""
from __future__ import annotations

from typing import Any

from ..core.models import RetrievedChunk
from ..stores.base import IndexStore
from . import bm25, dense


def _normalized(items: list[RetrievedChunk]) -> dict[str, tuple[RetrievedChunk, float]]:
    top = max((abs(i.score) for i in items), default=0.0) or 1.0
    return {i.chunk.id: (i, max(i.score, 0.0) / top) for i in items}


def search(store: IndexStore, query: str, query_vector: list[float], k: int, filters: dict[str, Any] | None = None,
           dense_weight: float = 0.7, candidates: int | None = None) -> list[RetrievedChunk]:
    pool = candidates or max(k * 4, 20)
    d = _normalized(dense.search(store, query_vector, pool, filters))
    s = _normalized(bm25.search(store, query, pool, filters))
    combined = []
    for chunk_id in set(d) | set(s):
        item = (d.get(chunk_id) or s[chunk_id])[0]
        score = dense_weight * d.get(chunk_id, (None, 0.0))[1] + (1 - dense_weight) * s.get(chunk_id, (None, 0.0))[1]
        combined.append((score, chunk_id, item))
    combined.sort(key=lambda t: (-t[0], t[1]))
    return [RetrievedChunk(item.chunk, round(score, 6), rank, "hybrid")
            for rank, (score, _, item) in enumerate(combined[:k], 1)]
