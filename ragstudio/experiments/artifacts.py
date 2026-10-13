"""Large per-run artifacts kept on disk (full context, raw result, diagnostics) with their SHA-256 in the database.

    Dados/runs/<run_id>/results.jsonl     one line per question: question, full TechniqueResult, metrics
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core import paths
from ..core.hashing import sha256_file


def run_dir(run_id: str) -> Path:
    path = paths.runs_dir() / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


class ResultWriter:
    def __init__(self, run_id: str) -> None:
        self.path = run_dir(run_id) / "results.jsonl"
        self._fh = open(self.path, "w", encoding="utf-8")  # noqa: SIM115 - closed in close()

    def write(self, record: dict[str, Any]) -> None:
        self._fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()

    def close(self) -> tuple[str, str]:
        self._fh.close()
        return str(self.path), sha256_file(self.path)


def read_results(run_id: str) -> list[dict[str, Any]]:
    path = paths.runs_dir() / run_id / "results.jsonl"
    if not path.is_file():
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
