"""Heuristic reranker: 0.7 * normalized retrieval score + 0.3 * fraction of query terms present in the chunk.

Ported from JudDoc_Ex `rag/retrieval.retrieve(reranker=True)`.
"""
from __future__ import annotations

from ..core.models import RetrievedChunk
from ..core.text import overlap


def rerank(query: str, chunks: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
    top = max((abs(c.score) for c in chunks), default=0.0) or 1.0
    scored = [(0.7 * max(c.score, 0.0) / top + 0.3 * overlap(query, c.chunk.text), c) for c in chunks]
    scored.sort(key=lambda t: (-t[0], t[1].chunk.id))
    return [c.with_rank(i, score=round(s, 6), source="rerank:lexical") for i, (s, c) in enumerate(scored[:k], 1)]
