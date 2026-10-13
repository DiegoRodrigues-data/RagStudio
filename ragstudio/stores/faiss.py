"""Optional FAISS-backed store (adapter). Vectors live in `<index dir>/index.faiss`.

Dense search is answered by a `faiss.IndexFlatIP` over L2-normalized vectors: exact cosine similarity, so the ranking
matches the default store and only the engine changes. Lexical search (BM25), lookups and the plain files are the
ones of `MemoryStore`. Requires `pip install faiss-cpu`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

from ..core.errors import NotFoundError, ValidationError
from .base import Hit, IndexMeta
from .memory import MemoryStore

INDEX_FILE = "index.faiss"


def _faiss() -> Any:
    # faiss-cpu and torch each bundle an OpenMP runtime; importing both aborts the interpreter on macOS (OMP error
    # 15), which would kill the command without a result line. Refuse instead.
    if "torch" in sys.modules and "faiss" not in sys.modules:
        raise ValidationError("the faiss store cannot be used in a process that already loaded PyTorch (conflicting "
                              "OpenMP runtimes); use another store or drop the cross_encoder reranker")
    try:
        import faiss
    except ImportError as exc:
        raise ValidationError("the faiss store needs the `faiss-cpu` package (pip install faiss-cpu)") from exc
    return faiss


class FaissStore(MemoryStore):
    """Same interface as MemoryStore; dense searches are answered by FAISS."""

    dense_backend = "faiss-flat-ip"

    def __init__(self, meta: IndexMeta, path: Path | None = None) -> None:
        super().__init__(meta, path)
        self.meta.store = "faiss"
        self._index: Any = None

    def add(self, chunks: list, embeddings: list[list[float]], index_texts: list[str] | None = None) -> None:
        super().add(chunks, embeddings, index_texts)
        self._index = None

    def _faiss_index(self) -> Any:
        if self._index is None:
            self._index = _faiss().IndexFlatIP(int(self._matrix.shape[1]))
            self._index.add(np.ascontiguousarray(self._matrix, dtype=np.float32))
        return self._index

    def dense_search(self, query_vector: list[float], k: int, filters: dict[str, Any] | None = None) -> list[Hit]:
        if not self._chunks or k <= 0:
            return []
        query = np.asarray(query_vector, dtype=np.float32)
        if query.shape[0] != self._matrix.shape[1]:
            raise ValidationError(f"embedding dimension mismatch: the query has {query.shape[0]} dims but the index "
                                  f"'{self.meta.index_hash[:12]}' ({self.meta.embedding_model}) has "
                                  f"{self._matrix.shape[1]}. Rebuild the index with the same embedding model.")
        query = query / (float(np.linalg.norm(query)) or 1.0)
        # A filter is applied after the search, so it needs the full ranking; the index is flat (exact) either way.
        fetch = len(self._chunks) if filters else min(k, len(self._chunks))
        scores, positions = self._faiss_index().search(query.reshape(1, -1), fetch)
        allowed = self._allowed(filters)
        found = [(int(p), float(s)) for p, s in zip(positions[0], scores[0], strict=True) if p >= 0 and allowed[p]]
        found.sort(key=lambda item: (-item[1], item[0]))
        return [(self._chunks[p], s) for p, s in found[:k]]

    def persist(self, path: Path) -> None:
        super().persist(path)
        if self._chunks:
            _faiss().write_index(self._faiss_index(), str(path / INDEX_FILE))

    @classmethod
    def load(cls, path: Path) -> FaissStore:
        if not (path / INDEX_FILE).is_file():
            raise NotFoundError(f"no FAISS index at {path}")
        base = MemoryStore.load(path)
        store = cls(base.meta, path)
        store._chunks, store._pos, store._index_texts = base._chunks, base._pos, base._index_texts
        store._matrix, store._documents = base._matrix, base._documents
        store._index = _faiss().read_index(str(path / INDEX_FILE))
        if store._index.ntotal != len(store._chunks):
            raise ValidationError(f"FAISS index at {path} has {store._index.ntotal} vectors for "
                                  f"{len(store._chunks)} chunks; rebuild it with `index build --force`")
        return store
