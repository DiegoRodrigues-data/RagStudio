"""Default index store: numpy matrix for dense search + Okapi BM25 for lexical search, persisted as plain files.

    Dados/indices/<index_hash>/{meta.json, chunks.jsonl, embeddings.npy, documents.jsonl, index_texts.jsonl, aux_*.json}
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from ..core.errors import NotFoundError, ValidationError
from ..core.models import Chunk
from ..core.text import tokenize
from .base import Hit, IndexMeta, matches

BM25_K1, BM25_B = 1.5, 0.75


class MemoryStore:
    def __init__(self, meta: IndexMeta, path: Path | None = None) -> None:
        self.meta = meta
        self.path = path
        self._chunks: list[Chunk] = []
        self._pos: dict[str, int] = {}
        self._index_texts: list[str] = []
        self._matrix = np.zeros((0, 0), dtype=np.float32)
        self._documents: dict[str, dict[str, Any]] = {}
        self._aux: dict[str, Any] = {}
        self._bm25: tuple[list[Counter[str]], dict[str, float], list[int], float] | None = None

    # ------------------------------------------------------------------ build
    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        for doc in documents:
            self._documents[doc["id"]] = doc
        self.meta.documents = len(self._documents)

    def add(self, chunks: list[Chunk], embeddings: list[list[float]], index_texts: list[str] | None = None) -> None:
        if len(chunks) != len(embeddings):
            raise ValidationError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")
        if not chunks:
            return
        matrix = np.asarray(embeddings, dtype=np.float32)
        if self._matrix.size and matrix.shape[1] != self._matrix.shape[1]:
            raise ValidationError(f"embedding dimension {matrix.shape[1]} differs from index dimension "
                                  f"{self._matrix.shape[1]}")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.where(norms == 0, 1.0, norms)
        self._matrix = matrix if not self._matrix.size else np.vstack([self._matrix, matrix])
        for chunk in chunks:
            self._pos[chunk.id] = len(self._chunks)
            self._chunks.append(chunk)
        self._index_texts.extend(index_texts or [c.text for c in chunks])
        self._bm25 = None
        self.meta.chunks, self.meta.dim = len(self._chunks), int(self._matrix.shape[1])

    # ----------------------------------------------------------------- search
    def _allowed(self, filters: dict[str, Any] | None) -> np.ndarray:
        if not filters:
            return np.ones(len(self._chunks), dtype=bool)
        return np.array([matches(c, self._documents.get(c.document_id, {}).get("metadata", {}), filters)
                         for c in self._chunks], dtype=bool)

    def _top(self, scores: np.ndarray, k: int, filters: dict[str, Any] | None, positive_only: bool) -> list[Hit]:
        if not len(self._chunks):
            return []
        mask = self._allowed(filters)
        if positive_only:
            mask &= scores > 0
        candidates = np.flatnonzero(mask)
        order = sorted(candidates.tolist(), key=lambda i: (-float(scores[i]), i))[:max(k, 0)]
        return [(self._chunks[i], float(scores[i])) for i in order]

    def dense_search(self, query_vector: list[float], k: int, filters: dict[str, Any] | None = None) -> list[Hit]:
        if not len(self._chunks):
            return []
        query = np.asarray(query_vector, dtype=np.float32)
        if query.shape[0] != self._matrix.shape[1]:
            raise ValidationError(f"embedding dimension mismatch: the query has {query.shape[0]} dims but the index "
                                  f"'{self.meta.index_hash[:12]}' ({self.meta.embedding_model}) has "
                                  f"{self._matrix.shape[1]}. Rebuild the index with the same embedding model.")
        norm = float(np.linalg.norm(query)) or 1.0
        return self._top(self._matrix @ (query / norm), k, filters, positive_only=False)

    def _bm25_state(self) -> tuple[list[Counter[str]], dict[str, float], list[int], float]:
        if self._bm25 is None:
            term_freqs = [Counter(tokenize(text)) for text in self._index_texts]
            lengths = [sum(tf.values()) for tf in term_freqs]
            df: Counter[str] = Counter()
            for tf in term_freqs:
                df.update(tf.keys())
            n = len(term_freqs)
            idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}
            self._bm25 = (term_freqs, idf, lengths, (sum(lengths) / n) if n else 0.0)
        return self._bm25

    def lexical_search(self, query: str, k: int, filters: dict[str, Any] | None = None) -> list[Hit]:
        term_freqs, idf, lengths, avg = self._bm25_state()
        terms = [t for t in tokenize(query) if t in idf]
        scores = np.zeros(len(term_freqs), dtype=np.float64)
        for i, tf in enumerate(term_freqs):
            total = 0.0
            for term in terms:
                f = tf.get(term, 0)
                if f:
                    total += idf[term] * f * (BM25_K1 + 1) / (f + BM25_K1 * (1 - BM25_B + BM25_B * lengths[i] / avg))
            scores[i] = total
        return self._top(scores, k, filters, positive_only=True)

    # ---------------------------------------------------------------- lookups
    def get(self, chunk_ids: list[str]) -> list[Chunk]:
        return [self._chunks[self._pos[cid]] for cid in chunk_ids if cid in self._pos]

    def all_chunks(self) -> list[Chunk]:
        return list(self._chunks)

    def embedding(self, chunk_id: str) -> list[float]:
        if chunk_id not in self._pos:
            raise NotFoundError(f"chunk '{chunk_id}' is not in this index")
        return self._matrix[self._pos[chunk_id]].astype(float).tolist()

    def embeddings_matrix(self) -> np.ndarray:
        return self._matrix

    def document_text(self, document_id: str) -> str:
        if document_id not in self._documents:
            raise NotFoundError(f"document '{document_id}' is not in this index")
        return self._documents[document_id]["text"]

    def document_ids(self) -> list[str]:
        return sorted(self._documents)

    # -------------------------------------------------------------- auxiliary
    def aux_load(self, name: str) -> Any | None:
        if name in self._aux:
            return self._aux[name]
        if self.path and (self.path / f"aux_{name}.json").is_file():
            self._aux[name] = json.loads((self.path / f"aux_{name}.json").read_text(encoding="utf-8"))
            return self._aux[name]
        return None

    def aux_save(self, name: str, data: Any) -> None:
        self._aux[name] = data
        if self.path:
            (self.path / f"aux_{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------ persistence
    def persist(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self.path = path
        (path / "meta.json").write_text(json.dumps(self.meta.to_dict(), ensure_ascii=False, indent=2), "utf-8")
        with open(path / "chunks.jsonl", "w", encoding="utf-8") as fh:
            for chunk in self._chunks:
                fh.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
        with open(path / "index_texts.jsonl", "w", encoding="utf-8") as fh:
            for text in self._index_texts:
                fh.write(json.dumps(text, ensure_ascii=False) + "\n")
        with open(path / "documents.jsonl", "w", encoding="utf-8") as fh:
            for doc in self._documents.values():
                fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
        np.save(path / "embeddings.npy", self._matrix)
        for name, data in self._aux.items():
            (path / f"aux_{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> MemoryStore:
        if not (path / "meta.json").is_file():
            raise NotFoundError(f"no index at {path}")
        meta = IndexMeta(**json.loads((path / "meta.json").read_text(encoding="utf-8")))
        store = cls(meta, path)
        with open(path / "documents.jsonl", encoding="utf-8") as fh:
            store.add_documents([json.loads(line) for line in fh if line.strip()])
        with open(path / "chunks.jsonl", encoding="utf-8") as fh:
            store._chunks = [Chunk.from_dict(json.loads(line)) for line in fh if line.strip()]
        with open(path / "index_texts.jsonl", encoding="utf-8") as fh:
            store._index_texts = [json.loads(line) for line in fh if line.strip()]
        store._pos = {c.id: i for i, c in enumerate(store._chunks)}
        store._matrix = np.load(path / "embeddings.npy")
        return store
