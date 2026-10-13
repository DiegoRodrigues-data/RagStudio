"""Cross-encoder reranker (adapter, optional): needs `pip install sentence-transformers` and a local model.

The default model is trained on English MS MARCO; for other languages pass a multilingual model. The offline
test-suite only covers the missing-dependency error: the model itself was exercised by hand (sentence-transformers
5.7.0), so treat it as an `adapter` until validated on your corpus.
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from ..core.errors import ValidationError
from ..core.models import RetrievedChunk

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=2)
def _model(model_name: str) -> Any:
    """One model per process: a runbook builds the reranker once per run, and loading takes seconds."""
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model_name)


def make(model_name: str = DEFAULT_MODEL) -> Callable[..., list[RetrievedChunk]]:
    if "faiss" in sys.modules and "torch" not in sys.modules:
        raise ValidationError("the cross_encoder reranker cannot be used in a process that already loaded FAISS "
                              "(conflicting OpenMP runtimes); use another store or another reranker")
    try:
        model = _model(model_name)
    except ImportError as exc:
        raise ValidationError("the cross_encoder reranker needs `pip install sentence-transformers`") from exc

    def rerank(query: str, chunks: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
        if not chunks:
            return []
        scores = model.predict([(query, c.chunk.text) for c in chunks])
        order = sorted(range(len(chunks)), key=lambda i: (-float(scores[i]), i))[:k]
        return [chunks[i].with_rank(rank, score=float(scores[i]), source="rerank:cross_encoder")
                for rank, i in enumerate(order, 1)]
    return rerank
