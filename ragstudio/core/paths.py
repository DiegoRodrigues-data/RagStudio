"""Filesystem layout. Everything is resolved at call time so tests can redirect it with RAGSTUDIO_* variables.

Never copy the result of these functions into a module-level constant.
"""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent


def project_root() -> Path:
    return PACKAGE_DIR.parent


def data_dir() -> Path:
    return _ensure(Path(os.environ.get("RAGSTUDIO_DATA_DIR") or project_root() / "Dados"))


def db_path() -> Path:
    return Path(os.environ.get("RAGSTUDIO_DB") or data_dir() / "ragstudio.sqlite")


def default_config_path() -> Path:
    return PACKAGE_DIR / "config" / "config.ini"


def local_config_path() -> Path:
    return Path(os.environ.get("RAGSTUDIO_CONFIG") or PACKAGE_DIR / "config" / "config.local.ini")


def input_dir() -> Path:
    return _ensure(data_dir() / "Input")


def output_dir() -> Path:
    return _ensure(data_dir() / "Output")


def indices_dir() -> Path:
    return _ensure(data_dir() / "indices")


def runs_dir() -> Path:
    return _ensure(data_dir() / "runs")


def exports_dir() -> Path:
    return _ensure(data_dir() / "exports")


def figures_dir() -> Path:
    return _ensure(data_dir() / "figures")


def backups_dir() -> Path:
    return _ensure(data_dir() / "backups")


def _ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
