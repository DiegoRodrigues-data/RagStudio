"""Reciprocal Rank Fusion (Cormack, Clarke & Büttcher, SIGIR 2009): score = sum(1 / (rrf_k + rank))."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..core.models import RetrievedChunk
from ..stores.base import IndexStore
from . import bm25, dense


def rrf(rankings: Iterable[list[RetrievedChunk]], k: int, rrf_k: int = 60) -> list[RetrievedChunk]:
    scores: dict[str, float] = {}
    items: dict[str, RetrievedChunk] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item.chunk.id] = scores.get(item.chunk.id, 0.0) + 1.0 / (rrf_k + rank)
            items.setdefault(item.chunk.id, item)
    order = sorted(scores, key=lambda cid: (-scores[cid], cid))[:k]
    return [RetrievedChunk(items[cid].chunk, round(scores[cid], 6), rank, "rrf") for rank, cid in enumerate(order, 1)]


def search(store: IndexStore, query: str, query_vector: list[float], k: int, filters: dict[str, Any] | None = None,
           rrf_k: int = 60, candidates: int | None = None) -> list[RetrievedChunk]:
    pool = candidates or max(k * 4, 20)
    return rrf([dense.search(store, query_vector, pool, filters), bm25.search(store, query, pool, filters)], k, rrf_k)
