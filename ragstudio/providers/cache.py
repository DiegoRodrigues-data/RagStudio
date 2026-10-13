"""Embedding cache keyed by (provider, model, sha256(text)): the same chunk is never paid for twice."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from ..core import paths
from ..core.hashing import sha256_text


class EmbeddingCache:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or paths.indices_dir() / "_embedding_cache.sqlite"
        self._con = sqlite3.connect(self.path)
        self._con.execute("CREATE TABLE IF NOT EXISTS embeddings (model_key TEXT NOT NULL, text_sha TEXT NOT NULL, "
                          "dim INTEGER NOT NULL, vector BLOB NOT NULL, PRIMARY KEY (model_key, text_sha))")

    @staticmethod
    def model_key(provider: str, model: str) -> str:
        return f"{provider}:{model}"

    def get_many(self, model_key: str, texts: list[str]) -> list[list[float] | None]:
        out: list[list[float] | None] = []
        for text in texts:
            row = self._con.execute("SELECT vector FROM embeddings WHERE model_key=? AND text_sha=?",
                                    (model_key, sha256_text(text))).fetchone()
            out.append(np.frombuffer(row[0], dtype=np.float32).astype(float).tolist() if row else None)
        return out

    def put_many(self, model_key: str, texts: list[str], vectors: list[list[float]]) -> None:
        rows = [(model_key, sha256_text(t), len(v), np.asarray(v, dtype=np.float32).tobytes())
                for t, v in zip(texts, vectors, strict=True)]
        with self._con:
            self._con.executemany("INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?)", rows)

    def close(self) -> None:
        self._con.close()
