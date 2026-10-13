"""Crossing results with corpus and document characteristics: the empirical-analysis view.

For every answered question, the "target document" is the document of its gold passages (or, without gold, the
top retrieved document). Its profile (size, structure, language...) is joined to the metrics, and per technique we
report the Spearman correlation between each characteristic and each metric, plus tercile bins by document size.

With few documents these correlations are descriptive only; `n` is reported with every number.
"""
from __future__ import annotations

import statistics
from typing import Any

from ..db.repository import Repo
from . import stats
from .compare import config_columns, runs_of

FEATURES = ("chars", "words", "paragraphs", "avg_paragraph_chars", "table_line_ratio", "list_line_ratio",
            "digit_ratio", "vocabulary_ratio", "headings")
METRICS = ("recall", "mrr", "ndcg", "context_coverage", "f1", "accuracy", "faithfulness", "latency_total")


def joined_rows(repo: Repo, runbook_refs: list[str]) -> list[dict[str, Any]]:
    rows = []
    profiles: dict[str, dict[str, dict[str, Any]]] = {}
    for run in runs_of(repo, runbook_refs):
        corpus = repo.get_corpus(run["config"]["corpus"])
        if corpus["id"] not in profiles:
            profiles[corpus["id"]] = {d["doc_id"]: d["profile"] for d in repo.document_rows(corpus["id"])}
        index = repo.get_index(run["index_hash"]) if run.get("index_hash") else {}
        chunk_profile = index.get("chunking_profile") or {}
        cols = config_columns(run)
        gold_docs: dict[str, str | None] = {}
        for result in repo.result_metrics(run["id"]):
            if result["error"]:
                continue
            qid = result["question_id"]
            if qid not in gold_docs:
                try:
                    gold = repo.get_question(qid)["gold_passages"]
                except Exception:  # noqa: BLE001 - question deleted after the run
                    gold = []
                gold_docs[qid] = gold[0]["document_id"] if gold else None
            target = gold_docs[qid]
            source = "gold"
            if target is None:
                chunks = repo.retrieved_chunks(result["query_result_id"])
                target, source = (chunks[0]["document_id"], "top_retrieved") if chunks else (None, "none")
            profile = profiles[corpus["id"]].get(target or "", {})
            rows.append({"run_id": run["id"], "technique": cols["technique"], "corpus": corpus["name"],
                         "chunking": cols["chunking"], "question_code": result["question_code"],
                         "target_document": target, "target_source": source,
                         "language": profile.get("language"), "format": profile.get("format"),
                         **{f"doc_{f}": profile.get(f) for f in FEATURES},
                         "index_chunks": chunk_profile.get("chunks"),
                         "index_chunk_chars_mean": chunk_profile.get("chunk_chars_mean"),
                         **{m: result.get(m) for m in METRICS}})
    return rows


def correlations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for technique in sorted({r["technique"] for r in rows}):
        subset = [r for r in rows if r["technique"] == technique]
        for metric in METRICS:
            for feature in FEATURES:
                pairs = [(r[f"doc_{feature}"], r[metric]) for r in subset
                         if r.get(f"doc_{feature}") is not None and r.get(metric) is not None]
                rho = stats.spearman([p[0] for p in pairs], [p[1] for p in pairs]) if pairs else None
                if rho is not None:
                    out.append({"technique": technique, "metric": metric, "feature": feature, "spearman": rho,
                                "n": len(pairs), "documents": len({p[0] for p in pairs})})
    return sorted(out, key=lambda r: -abs(r["spearman"]))


def size_bins(rows: list[dict[str, Any]], feature: str = "chars") -> list[dict[str, Any]]:
    """Mean metrics per technique within terciles of a document feature (default: document size)."""
    values = sorted({r[f"doc_{feature}"] for r in rows if r.get(f"doc_{feature}") is not None})
    if len(values) < 3:
        return []
    low, high = values[len(values) // 3], values[2 * len(values) // 3]
    label = lambda v: "small" if v < low else "large" if v >= high else "medium"  # noqa: E731
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(f"doc_{feature}")
        if value is not None:
            groups.setdefault((row["technique"], label(value)), []).append(row)
    out = []
    for (technique, bin_label), members in sorted(groups.items()):
        entry: dict[str, Any] = {"technique": technique, "bin": bin_label, "feature": feature, "n": len(members)}
        for metric in METRICS:
            vals = [m[metric] for m in members if m.get(metric) is not None]
            entry[metric] = round(statistics.fmean(vals), 4) if vals else None
        out.append(entry)
    return out


def by_group(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Mean metrics per technique for each value of a categorical characteristic (language, format, corpus)."""
    groups: dict[tuple[str, Any], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["technique"], row.get(key)), []).append(row)
    out = []
    for (technique, value), members in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        entry: dict[str, Any] = {"technique": technique, key: value, "n": len(members)}
        for metric in METRICS:
            vals = [m[metric] for m in members if m.get(metric) is not None]
            entry[metric] = round(statistics.fmean(vals), 4) if vals else None
        out.append(entry)
    return out


def analyze(repo: Repo, runbook_refs: list[str]) -> dict[str, Any]:
    rows = joined_rows(repo, runbook_refs)
    documents = {r["target_document"] for r in rows if r["target_document"]}
    return {"rows": len(rows), "documents": len(documents),
            "target_sources": {s: sum(1 for r in rows if r["target_source"] == s)
                               for s in sorted({r["target_source"] for r in rows})},
            "correlations": correlations(rows), "size_bins": size_bins(rows),
            "by_language": by_group(rows, "language"), "by_format": by_group(rows, "format"),
            "by_corpus": by_group(rows, "corpus"),
            "note": "descriptive statistics; with few documents (see `documents`) do not read them as effects"}
