"""Numbered SQL migrations (`migrations/NNNN_name.sql`), applied once, in order."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def available() -> list[tuple[int, str, Path]]:
    out = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        out.append((int(path.name[:4]), path.stem[5:], path))
    return out


def applied(con: sqlite3.Connection) -> list[int]:
    exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone()
    if not exists:
        return []
    return [row[0] for row in con.execute("SELECT version FROM schema_version ORDER BY version")]


def migrate(con: sqlite3.Connection) -> dict[str, Any]:
    done = set(applied(con))
    newly = []
    for version, name, path in available():
        if version in done:
            continue
        con.executescript(path.read_text(encoding="utf-8"))
        con.execute("INSERT INTO schema_version VALUES (?, ?, ?)",
                    (version, name, datetime.now(UTC).isoformat(timespec="seconds")))
        newly.append(version)
    return {"applied": newly, "version": max(applied(con), default=0)}


def status(con: sqlite3.Connection) -> dict[str, Any]:
    done = applied(con)
    pending = [v for v, _, _ in available() if v not in done]
    return {"version": max(done, default=0), "applied": done, "pending": pending}
