"""Reranker factory. `none` means the run has no reranker (techniques fall back to score order)."""
from __future__ import annotations

import importlib.util
from collections.abc import Callable
from typing import Any

from ..core.errors import ValidationError
from ..core.models import RetrievedChunk
from . import lexical, llm, noop

NAMES = ("none", "lexical", "llm", "cross_encoder")
Reranker = Callable[[str, list[RetrievedChunk], int], list[RetrievedChunk]]
REQUIRES = {"cross_encoder": ("sentence_transformers", "sentence-transformers")}


def missing_dependency(name: str) -> str | None:
    """The pip package a reranker needs and that is not installed, or None. Checked before a runbook starts, so a
    missing package fails once at validation instead of failing every run that uses it."""
    module, package = REQUIRES.get(name, (None, None))
    return package if module and importlib.util.find_spec(module) is None else None


def build(name: str | None, ask: Callable[..., str] | None = None, **options: Any) -> Reranker | None:
    name = (name or "none").lower()
    if name == "none":
        return None
    if name == "lexical":
        return lexical.rerank
    if name == "llm":
        if ask is None:
            raise ValidationError("the llm reranker needs an LLM")
        return llm.make(ask, **options)
    if name == "cross_encoder":
        from . import cross_encoder
        return cross_encoder.make(**options)
    raise ValidationError(f"unknown reranker '{name}' (available: {NAMES})")


__all__ = ["build", "missing_dependency", "NAMES", "Reranker", "noop"]
