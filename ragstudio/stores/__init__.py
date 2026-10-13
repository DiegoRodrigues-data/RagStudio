"""Store factory: `create(kind, meta)` and `load(path)`."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ..core.errors import NotFoundError, ValidationError
from .base import IndexMeta, IndexStore
from .memory import MemoryStore

KINDS = ("memory", "duckdb", "faiss", "chroma")
REQUIRES = {"duckdb": ("duckdb", "duckdb"), "faiss": ("faiss", "faiss-cpu"), "chroma": ("chromadb", "chromadb")}


def missing_dependency(kind: str) -> str | None:
    """The pip package a store needs and that is not installed, or None."""
    module, package = REQUIRES.get(kind, (None, None))
    return package if module and importlib.util.find_spec(module) is None else None


def create(kind: str, meta: IndexMeta) -> MemoryStore:
    if kind == "memory":
        return MemoryStore(meta)
    if kind == "duckdb":
        from .duckdb import DuckDBStore, _duckdb
        _duckdb()
        return DuckDBStore(meta)
    if kind == "faiss":
        from .faiss import FaissStore, _faiss
        _faiss()
        return FaissStore(meta)
    if kind == "chroma":
        from .chroma import ChromaStore, _chromadb
        _chromadb()
        return ChromaStore(meta)
    raise ValidationError(f"unknown store '{kind}' (available: {KINDS})")


def load(path: Path) -> MemoryStore:
    meta_file = path / "meta.json"
    if not meta_file.is_file():
        raise NotFoundError(f"no index at {path}")
    kind = json.loads(meta_file.read_text(encoding="utf-8")).get("store", "memory")
    if kind == "duckdb":
        from .duckdb import DuckDBStore
        return DuckDBStore.load(path)
    if kind == "faiss":
        from .faiss import FaissStore
        return FaissStore.load(path)
    if kind == "chroma":
        from .chroma import ChromaStore
        return ChromaStore.load(path)
    return MemoryStore.load(path)


__all__ = ["IndexMeta", "IndexStore", "MemoryStore", "create", "load", "missing_dependency", "KINDS"]
