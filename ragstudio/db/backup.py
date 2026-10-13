"""Database backups: explicit (`db backup`) and automatic before guarded deletions (last 10 kept)."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from ..core import paths

KEEP_AUTO = 10


def backup(con: sqlite3.Connection, output: Path | None = None, auto: bool = False) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = output or paths.backups_dir() / f"{'auto' if auto else 'manual'}_{stamp}.sqlite"
    target.parent.mkdir(parents=True, exist_ok=True)
    dest = sqlite3.connect(target)
    try:
        con.backup(dest)
    finally:
        dest.close()
    if auto:
        for old in sorted(paths.backups_dir().glob("auto_*.sqlite"))[:-KEEP_AUTO]:
            old.unlink(missing_ok=True)
    return target
