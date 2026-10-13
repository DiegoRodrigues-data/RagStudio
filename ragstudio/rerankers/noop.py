"""No reranking: keep the incoming order and cut to k."""
from __future__ import annotations

from ..core.models import RetrievedChunk


def rerank(query: str, chunks: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
    return [c.with_rank(i) for i, c in enumerate(chunks[:k], 1)]
