"""Index store contract: where chunks, their embeddings and the source documents live for one index.

An index is identified by `index_hash = sha256(corpus content, split, chunking, embedding model, enrichment)`, so
techniques that share the same indexing reuse the same vectors and are compared on equal footing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..core.models import Chunk


@dataclass
class IndexMeta:
    index_hash: str
    corpus_id: str
    chunking: dict[str, Any]
    embedding_model: str
    embedding_provider: str = ""
    dim: int = 0
    store: str = "memory"
    split: str | None = None
    enrich: str | None = None
    chunks: int = 0
    documents: int = 0
    created_at: str = ""
    chunking_profile: dict[str, Any] = field(default_factory=dict)
    build_usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Hit = tuple[Chunk, float]


class IndexStore(Protocol):
    meta: IndexMeta

    def add_documents(self, documents: list[dict[str, Any]]) -> None: ...
    def add(self, chunks: list[Chunk], embeddings: list[list[float]], index_texts: list[str] | None = None) -> None: ...
    def dense_search(self, query_vector: list[float], k: int, filters: dict[str, Any] | None = None) -> list[Hit]: ...
    def lexical_search(self, query: str, k: int, filters: dict[str, Any] | None = None) -> list[Hit]: ...
    def get(self, chunk_ids: list[str]) -> list[Chunk]: ...
    def all_chunks(self) -> list[Chunk]: ...
    def embedding(self, chunk_id: str) -> list[float]: ...
    def document_text(self, document_id: str) -> str: ...
    def aux_load(self, name: str) -> Any | None: ...
    def aux_save(self, name: str, data: Any) -> None: ...
    def persist(self, path: Path) -> None: ...


def matches(chunk: Chunk, doc_meta: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    """`filters` maps a key to a value or list of values. Keys: document_id, chunk metadata, document metadata."""
    if not filters:
        return True
    for key, wanted in filters.items():
        allowed = wanted if isinstance(wanted, (list, tuple, set)) else [wanted]
        if key == "document_id":
            value: Any = chunk.document_id
        elif key in chunk.metadata:
            value = chunk.metadata[key]
        else:
            value = doc_meta.get(key)
        if value not in allowed:
            return False
    return True
