"""RAG-EVO confidence modes: composite (default), heuristic (length only) and llm (self-rating).

Ported from `ragkit/evo_utils.py`.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from .heuristics import confidence_score

MODES = ("composite", "heuristic", "llm")
LLM_FALLBACK = 0.5


def heuristic_confidence(answer: str, min_len: int = 250) -> float:
    if not answer:
        return 0.0
    return 0.75 if len(answer) >= min_len else 0.4


def llm_confidence(ask: Callable[..., str], query: str, answer: str, context: str) -> tuple[float, bool]:
    """(score, parsed). An unparseable self-rating yields the neutral fallback and parsed=False."""
    raw = ask("confidence", query=query, answer=answer[:4000], context=context[:4000])
    match = re.search(r"\d+(?:[.,]\d+)?", raw)
    if not match:
        return LLM_FALLBACK, False
    return max(0.0, min(1.0, float(match.group(0).replace(",", ".")))), True


def evaluate(mode: str, ask: Callable[..., str], query: str, answer: str, context_text: str,
             context_texts: list[str], weights: dict[str, float], target_chars: int) -> dict[str, Any]:
    if mode == "llm":
        score, parsed = llm_confidence(ask, query, answer, context_text)
        return {"confidence": score, "mode": mode, "parsed": parsed}
    if mode == "heuristic":
        return {"confidence": heuristic_confidence(answer), "mode": mode}
    return {**confidence_score(answer, context_texts, target_chars=target_chars, **weights), "mode": "composite"}
