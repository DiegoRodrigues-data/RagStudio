"""Dense retrieval: cosine similarity between the query vector and the chunk vectors."""
from __future__ import annotations

from typing import Any

from ..core.models import RetrievedChunk
from ..stores.base import IndexStore


def search(store: IndexStore, query_vector: list[float], k: int,
           filters: dict[str, Any] | None = None) -> list[RetrievedChunk]:
    hits = store.dense_search(query_vector, k, filters)
    return [RetrievedChunk(chunk, score, rank, "dense") for rank, (chunk, score) in enumerate(hits, 1)]
