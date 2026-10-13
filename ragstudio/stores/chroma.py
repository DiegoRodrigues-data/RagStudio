"""Optional Chroma-backed store (adapter). The collection lives in `<index dir>/chroma/`.

Dense search is answered by a persistent Chroma collection with an HNSW index in cosine space. HNSW is an
approximate nearest-neighbour search: on large indices the ranking may differ from the exact stores (`memory`,
`faiss`), which is the point of offering it as an experiment variable. Vectors are always the ones computed by the
configured embedding endpoint; Chroma's own embedding function is never used. Lexical search (BM25), lookups and the
plain files are the ones of `MemoryStore`. Requires `pip install chromadb`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.errors import NotFoundError, ValidationError
from .base import Hit, IndexMeta
from .memory import MemoryStore

DIRECTORY = "chroma"
COLLECTION = "chunks"
# Chroma keeps one live system per directory in the process. A rebuilt index deletes and rewrites that directory, so
# the client that was serving the old files has to be closed first, or the new one writes through a stale handle.
_OPEN: dict[str, Any] = {}


def _chromadb() -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise ValidationError("the chroma store needs the `chromadb` package (pip install chromadb)") from exc
    return chromadb


class ChromaStore(MemoryStore):
    """Same interface as MemoryStore; dense searches are answered by Chroma once the index is persisted."""

    dense_backend = "chroma-hnsw-cosine"

    def __init__(self, meta: IndexMeta, path: Path | None = None) -> None:
        super().__init__(meta, path)
        self.meta.store = "chroma"
        self._collection: Any = None

    def _client(self, path: Path, fresh: bool = False) -> Any:
        chromadb = _chromadb()
        from chromadb.config import Settings
        directory = str((path / DIRECTORY).resolve())
        if fresh and directory in _OPEN:
            _OPEN.pop(directory).close()
        if directory not in _OPEN:
            _OPEN[directory] = chromadb.PersistentClient(path=directory, settings=Settings(anonymized_telemetry=False))
        return _OPEN[directory]

    def _sync(self, path: Path) -> None:
        client = self._client(path, fresh=True)
        if COLLECTION in [c.name for c in client.list_collections()]:
            client.delete_collection(COLLECTION)
        collection = client.create_collection(COLLECTION, configuration={"hnsw": {"space": "cosine"}},
                                              embedding_function=None)
        batch = int(client.get_max_batch_size())
        for start in range(0, len(self._chunks), batch):
            rows = self._chunks[start:start + batch]
            collection.add(ids=[str(start + i) for i in range(len(rows))],
                           embeddings=self._matrix[start:start + batch].astype(float).tolist(),
                           metadatas=[{"chunk_id": c.id, "document_id": c.document_id} for c in rows])
        self._collection = collection

    def dense_search(self, query_vector: list[float], k: int, filters: dict[str, Any] | None = None) -> list[Hit]:
        if self._collection is None or not self._chunks:
            return super().dense_search(query_vector, k, filters)
        if k <= 0:
            return []
        if len(query_vector) != self.meta.dim:
            raise ValidationError(f"embedding dimension mismatch: the query has {len(query_vector)} dims but the "
                                  f"index '{self.meta.index_hash[:12]}' ({self.meta.embedding_model}) has "
                                  f"{self.meta.dim}. Rebuild the index with the same embedding model.")
        # A filter is applied after the search, so it asks Chroma for the full ranking.
        fetch = len(self._chunks) if filters else min(k, len(self._chunks))
        result = self._collection.query(query_embeddings=[list(map(float, query_vector))], n_results=fetch,
                                        include=["distances"])
        allowed = self._allowed(filters)
        found = [(int(i), 1.0 - float(d)) for i, d in zip(result["ids"][0], result["distances"][0], strict=True)
                 if allowed[int(i)]]
        found.sort(key=lambda item: (-item[1], item[0]))
        return [(self._chunks[p], s) for p, s in found[:k]]

    def persist(self, path: Path) -> None:
        super().persist(path)
        if self._chunks:
            self._sync(path)

    @classmethod
    def load(cls, path: Path) -> ChromaStore:
        if not (path / DIRECTORY).is_dir():
            raise NotFoundError(f"no Chroma index at {path}")
        base = MemoryStore.load(path)
        store = cls(base.meta, path)
        store._chunks, store._pos, store._index_texts = base._chunks, base._pos, base._index_texts
        store._matrix, store._documents = base._matrix, base._documents
        try:
            store._collection = store._client(path).get_collection(COLLECTION, embedding_function=None)
        except Exception as exc:  # noqa: BLE001 - chromadb raises its own error types
            raise NotFoundError(f"no Chroma collection at {path}: {exc}") from exc
        if store._collection.count() != len(store._chunks):
            raise ValidationError(f"Chroma collection at {path} has {store._collection.count()} vectors for "
                                  f"{len(store._chunks)} chunks; rebuild it with `index build --force`")
        return store
