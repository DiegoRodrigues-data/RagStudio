"""Analytical exports (CSV, JSON, Parquet) written to Dados/exports with their SHA-256 registered in the database."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core import paths
from ..core.errors import ValidationError
from ..core.hashing import sha256_file
from ..db.repository import Repo
from . import characteristics, compare

FORMATS = ("csv", "json", "parquet")
TABLES = ("runs", "questions", "characteristics")
SCHEMA = {
    "runs": "one row per completed run: configuration axes (technique, retrieval_mode, reranker, k, seed, llm, "
            "embedding_model, chunking...), config_hash, index_hash and the aggregated metrics of the latest "
            "evaluation (means, *_n = questions measured, *_stdev, latency_<stage>, tokens, cost_usd)",
    "questions": "one row per run x question: configuration axes, latency_total and latency_<stage>, llm_calls, "
                 "tokens, cost_usd, context_chars, retrieval metrics (k, gold_count, hit, recall, precision, mrr, "
                 "ndcg, context_coverage) and generation metrics (exact_match, f1, accuracy, faithfulness, "
                 "groundedness, citation_accuracy, hallucination, refusal, judge_*). Empty = not measurable",
    "characteristics": "one row per run x question joined with the profile of the target document (doc_chars, "
                       "doc_words, doc_table_line_ratio, language, format...) and of the index (index_chunks, "
                       "index_chunk_chars_mean)",
}


def table(repo: Repo, name: str, runbook_refs: list[str]) -> list[dict[str, Any]]:
    if name == "runs":
        return compare.run_table(repo, runbook_refs)
    if name == "questions":
        return compare.question_table(repo, runbook_refs)
    if name == "characteristics":
        return characteristics.joined_rows(repo, runbook_refs)
    raise ValidationError(f"unknown table '{name}' (available: {TABLES})")


def _flat(value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value


def write(rows: list[dict[str, Any]], path: Path, fmt: str) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    elif fmt == "csv":
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            writer.writerows({k: _flat(v) for k, v in row.items()} for row in rows)
    elif fmt == "parquet":
        try:
            import pandas as pd
            pd.DataFrame([{k: _flat(row.get(k)) for k in columns} for row in rows]).to_parquet(path, index=False)
        except ImportError as exc:
            raise ValidationError("parquet export needs pandas and pyarrow (pip install pyarrow)") from exc
    else:
        raise ValidationError(f"unknown export format '{fmt}' (available: {FORMATS})")


def export(repo: Repo, name: str, runbook_refs: list[str], fmt: str = "csv",
           output: str | None = None) -> dict[str, Any]:
    rows = table(repo, name, runbook_refs)
    if not rows:
        raise ValidationError("nothing to export: no completed runs in the given runbooks")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output).expanduser() if output else paths.exports_dir() / f"{name}_{stamp}.{fmt}"
    write(rows, path, fmt)
    digest = sha256_file(path)
    repo.add_export(f"table:{name}", ",".join(runbook_refs), fmt, str(path), digest)
    return {"table": name, "format": fmt, "rows": len(rows), "path": str(path), "sha256": digest}
