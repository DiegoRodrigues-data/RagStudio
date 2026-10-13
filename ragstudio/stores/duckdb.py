"""Optional DuckDB-backed store (adapter). Ported from `ragkit/duckdb_schema.py` and `ragkit/duckdb_store.py`.

Chunks and vectors live in `<index dir>/index.duckdb`. Dense search runs in SQL (`list_cosine_similarity`); lexical
search uses the DuckDB FTS extension (BM25) when it can be loaded and otherwise falls back to the same in-memory
BM25 as the default store (recorded in `lexical_backend`). Requires `pip install duckdb`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.errors import NotFoundError, ValidationError
from .base import Hit, IndexMeta, matches
from .memory import MemoryStore


def _duckdb() -> Any:
    try:
        import duckdb
    except ImportError as exc:
        raise ValidationError("the duckdb store needs the `duckdb` package (pip install duckdb)") from exc
    return duckdb


class DuckDBStore(MemoryStore):
    """Same interface as MemoryStore; searches are answered by DuckDB. The in-memory copy serves lookups."""

    def __init__(self, meta: IndexMeta, path: Path | None = None) -> None:
        super().__init__(meta, path)
        self.meta.store = "duckdb"
        self._con: Any = None
        self.lexical_backend = "memory-bm25"

    def _connect(self, path: Path) -> Any:
        if self._con is None:
            self._con = _duckdb().connect(str(path / "index.duckdb"))
        return self._con

    def _sync(self, path: Path) -> None:
        con = self._connect(path)
        con.execute("DROP TABLE IF EXISTS docs")
        con.execute("CREATE TABLE docs (pos INTEGER, chunk_id VARCHAR, doc_id VARCHAR, text VARCHAR, "
                    "embedding FLOAT[])")
        rows = [(i, c.id, c.document_id, self._index_texts[i], self._matrix[i].astype(float).tolist())
                for i, c in enumerate(self._chunks)]
        if rows:
            con.executemany("INSERT INTO docs VALUES (?,?,?,?,?)", rows)
        try:
            con.execute("INSTALL fts")
            con.execute("LOAD fts")
            con.execute("PRAGMA create_fts_index('docs', 'chunk_id', 'text', overwrite=1)")
            self.lexical_backend = "duckdb-fts"
        except Exception:  # noqa: BLE001 - extension unavailable (offline): documented fallback
            self.lexical_backend = "memory-bm25"

    def dense_search(self, query_vector: list[float], k: int, filters: dict[str, Any] | None = None) -> list[Hit]:
        if self._con is None or not self._chunks:
            return super().dense_search(query_vector, k, filters)
        if len(query_vector) != self.meta.dim:
            raise ValidationError(f"embedding dimension mismatch: query {len(query_vector)} vs index {self.meta.dim}")
        rows = self._con.execute("SELECT pos, list_cosine_similarity(embedding, ?::FLOAT[]) AS score FROM docs "
                                 "ORDER BY score DESC, pos", [list(map(float, query_vector))]).fetchall()
        return self._filtered(rows, k, filters)

    def lexical_search(self, query: str, k: int, filters: dict[str, Any] | None = None) -> list[Hit]:
        if self._con is None or self.lexical_backend != "duckdb-fts":
            return super().lexical_search(query, k, filters)
        rows = self._con.execute("SELECT pos, score FROM (SELECT pos, fts_main_docs.match_bm25(chunk_id, ?) AS score "
                                 "FROM docs) WHERE score IS NOT NULL ORDER BY score DESC, pos", [query]).fetchall()
        return self._filtered(rows, k, filters)

    def _filtered(self, rows: list[tuple[int, float]], k: int, filters: dict[str, Any] | None) -> list[Hit]:
        out: list[Hit] = []
        for pos, score in rows:
            chunk = self._chunks[pos]
            if matches(chunk, self._documents.get(chunk.document_id, {}).get("metadata", {}), filters):
                out.append((chunk, float(score)))
                if len(out) >= k:
                    break
        return out

    def persist(self, path: Path) -> None:
        super().persist(path)
        self._sync(path)
        (path / "meta.json").write_text(json.dumps({**self.meta.to_dict()}, ensure_ascii=False, indent=2), "utf-8")

    @classmethod
    def load(cls, path: Path) -> DuckDBStore:
        if not (path / "index.duckdb").is_file():
            raise NotFoundError(f"no DuckDB index at {path}")
        base = MemoryStore.load(path)
        store = cls(base.meta, path)
        store._chunks, store._pos, store._index_texts = base._chunks, base._pos, base._index_texts
        store._matrix, store._documents = base._matrix, base._documents
        con = store._connect(path)
        try:
            con.execute("LOAD fts")
            con.execute("SELECT fts_main_docs.match_bm25(chunk_id, 'x') FROM docs LIMIT 1")
            store.lexical_backend = "duckdb-fts"
        except Exception:  # noqa: BLE001
            store.lexical_backend = "memory-bm25"
        return store
