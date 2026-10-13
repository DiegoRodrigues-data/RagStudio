"""`ragstudio db ...`: schema migrations, integrity, backup."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..core import paths
from ..db import migrate as migrate_mod
from ..db.connection import connect
from ..db.repository import Repo
from .common import command


def _migrate(args: argparse.Namespace) -> Any:
    con = connect()
    try:
        return {"database": str(paths.db_path()), **migrate_mod.migrate(con)}
    finally:
        con.close()


def _status(args: argparse.Namespace) -> Any:
    con = connect()
    try:
        state = migrate_mod.status(con)
    finally:
        con.close()
    with Repo() as repo:
        return {"database": str(paths.db_path()), **state, "counts": repo.counts()}


def _integrity(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return repo.integrity_check()


def _backup(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return {"path": repo.backup(Path(args.output).expanduser() if args.output else None)}


def _vacuum(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        repo.vacuum()
    return {"vacuumed": True}


def register(groups: Any) -> None:
    sub = groups.add_parser("db", help="database schema and maintenance").add_subparsers(dest="command", required=True)
    command(sub, "migrate", _migrate, "apply pending migrations")
    command(sub, "status", _status, "schema version and row counts")
    command(sub, "integrity-check", _integrity, "SQLite integrity and foreign-key check")
    command(sub, "backup", _backup, "copy the database").add_argument("--output")
    command(sub, "vacuum", _vacuum, "rebuild the database file")
