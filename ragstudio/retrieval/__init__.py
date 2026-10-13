"""Retrieval dispatcher: one entry point, five modes, all returning ranked `RetrievedChunk`s."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..core.errors import ValidationError
from ..core.models import RetrievedChunk
from ..stores.base import IndexStore
from . import bm25, dense, fusion, hybrid, mmr

MODES = ("dense", "bm25", "hybrid", "rrf", "mmr")


def retrieve(store: IndexStore, embed_query: Callable[[str], list[float]], query: str, k: int, *,
             mode: str = "dense", query_vector: list[float] | None = None, filters: dict[str, Any] | None = None,
             **options: Any) -> list[RetrievedChunk]:
    """`query_vector` overrides the embedding of `query` (HyDE). `options` are mode specific:
    hybrid: dense_weight, candidates · rrf: rrf_k, candidates · mmr: lambda_, k_candidates."""
    if mode not in MODES:
        raise ValidationError(f"unknown retrieval mode '{mode}' (available: {MODES})")
    if k <= 0:
        return []
    if mode == "bm25":
        return bm25.search(store, query, k, filters)
    vector = query_vector if query_vector is not None else embed_query(query)
    if mode == "dense":
        return dense.search(store, vector, k, filters)
    if mode == "hybrid":
        return hybrid.search(store, query, vector, k, filters, **_pick(options, "dense_weight", "candidates"))
    if mode == "rrf":
        return fusion.search(store, query, vector, k, filters, **_pick(options, "rrf_k", "candidates"))
    return mmr.search(store, vector, k, filters, **_pick(options, "lambda_", "k_candidates"))


def _pick(options: dict[str, Any], *names: str) -> dict[str, Any]:
    return {n: options[n] for n in names if options.get(n) is not None}
