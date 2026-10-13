"""Lexical retrieval (Okapi BM25, or the store's native full-text index)."""
from __future__ import annotations

from typing import Any

from ..core.models import RetrievedChunk
from ..stores.base import IndexStore


def search(store: IndexStore, query: str, k: int, filters: dict[str, Any] | None = None) -> list[RetrievedChunk]:
    hits = store.lexical_search(query, k, filters)
    return [RetrievedChunk(chunk, score, rank, "bm25") for rank, (chunk, score) in enumerate(hits, 1)]
