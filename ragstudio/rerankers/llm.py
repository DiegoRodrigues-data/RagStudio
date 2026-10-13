"""LLM list reranker: the model returns the passage numbers in order. Ported from `ragkit.make_rerank_llm`.

The answer is parsed defensively: unknown or repeated numbers are ignored and passages the model left out keep
their original relative order at the end, so a malformed answer degrades to the incoming order instead of failing.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from ..core.models import RetrievedChunk

Ask = Callable[..., str]


def parse_order(raw: str, n: int) -> list[int]:
    seen: list[int] = []
    for token in re.findall(r"\d+", raw):
        idx = int(token) - 1
        if 0 <= idx < n and idx not in seen:
            seen.append(idx)
    return seen + [i for i in range(n) if i not in seen]


def make(ask: Ask, max_candidates: int = 20, passage_chars: int = 600) -> Callable[..., list[RetrievedChunk]]:
    def rerank(query: str, chunks: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
        head, tail = chunks[:max_candidates], chunks[max_candidates:]
        if len(head) < 2:
            return [c.with_rank(i) for i, c in enumerate(chunks[:k], 1)]
        raw = ask("rerank", query=query, passages=[c.chunk.text[:passage_chars] for c in head])
        ordered = [head[i] for i in parse_order(raw, len(head))] + tail
        return [c.with_rank(i, score=round(1.0 / i, 6), source="rerank:llm") for i, c in enumerate(ordered[:k], 1)]
    return rerank
