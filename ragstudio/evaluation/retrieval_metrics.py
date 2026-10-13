"""Retrieval metrics against gold passages: hit@k, recall@k, precision@k, MRR, nDCG@k and context coverage.

A retrieved chunk is relevant to a gold passage of the same document when
- the gold passage has offsets and the chunk covers at least half of it, or
- the normalized gold text is contained in the chunk text (or the chunk in the gold text).

Returns None when the question has no gold passages: the metric is unavailable, not zero.
"""
from __future__ import annotations

import math
from typing import Any

from ..core.text import content_tokens, normalize

MIN_OVERLAP = 0.5


def is_relevant(chunk: dict[str, Any], gold: dict[str, Any]) -> bool:
    if chunk["document_id"] != gold["document_id"]:
        return False
    g_start, g_end = gold.get("char_start"), gold.get("char_end")
    if g_start is not None and g_end is not None and g_end > g_start:
        covered = min(chunk["char_end"], g_end) - max(chunk["char_start"], g_start)
        if covered / (g_end - g_start) >= MIN_OVERLAP:
            return True
    gold_text, chunk_text = normalize(gold["text"]), normalize(chunk["text"])
    return bool(gold_text) and (gold_text in chunk_text or (len(chunk_text) > 40 and chunk_text in gold_text))


def context_coverage(context_text: str, gold_passages: list[dict[str, Any]]) -> float:
    """Mean share of each gold passage's content tokens present in the final context sent to the model."""
    context_tokens = set(content_tokens(context_text))
    shares = []
    for gold in gold_passages:
        tokens = set(content_tokens(gold["text"]))
        if tokens:
            shares.append(len(tokens & context_tokens) / len(tokens))
    return round(sum(shares) / len(shares), 4) if shares else 0.0


def evaluate(chunks: list[dict[str, Any]], gold_passages: list[dict[str, Any]],
             context_text: str = "") -> dict[str, Any] | None:
    """`chunks` are the technique's final ranked chunks (dicts with document_id, char_start, char_end, text)."""
    if not gold_passages:
        return None
    k = len(chunks)
    relevance = [[is_relevant(chunk, gold) for gold in gold_passages] for chunk in chunks]
    relevant_flags = [any(row) for row in relevance]
    found = sum(1 for g in range(len(gold_passages)) if any(row[g] for row in relevance))
    first = next((rank for rank, flag in enumerate(relevant_flags, 1) if flag), None)
    dcg = sum(1.0 / math.log2(rank + 1) for rank, flag in enumerate(relevant_flags, 1) if flag)
    ideal_count = min(k, max(len(gold_passages), sum(relevant_flags)))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return {"k": k, "gold_count": len(gold_passages), "hit": 1.0 if first else 0.0,
            "recall": round(found / len(gold_passages), 4),
            "precision": round(sum(relevant_flags) / k, 4) if k else 0.0,
            "mrr": round(1.0 / first, 4) if first else 0.0,
            "ndcg": round(dcg / idcg, 4) if idcg else 0.0,
            "context_coverage": context_coverage(context_text, gold_passages)}
