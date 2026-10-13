"""SQLite connection: WAL, foreign keys on, busy timeout, rows as dict-like objects."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..core import paths


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or paths.db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(target, timeout=30, isolation_level=None)  # autocommit; transactions are explicit
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    return con


@contextmanager
def transaction(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")
