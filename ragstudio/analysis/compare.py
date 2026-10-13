"""Comparison tables: by run, by question, by any configuration axis, and paired run-vs-run comparison."""
from __future__ import annotations

import json
import statistics
from typing import Any

from ..core.errors import ValidationError
from ..db.repository import Repo
from ..evaluation.aggregate import MEAN_METRICS
from . import stats

CONFIG_COLUMNS = ("technique", "retrieval_mode", "reranker", "k", "seed", "llm", "embedding_model", "store",
                  "enrich", "corpus", "split", "language", "provider")
EFFICIENCY = ("latency_total", "llm_calls", "prompt_tokens", "completion_tokens", "embedding_tokens", "cost_usd",
              "context_chars")
NOT_APPLICABLE = "n/a"
GROUP_KEYS = ("technique", "corpus", "chunking", "retrieval_mode", "reranker", "k", "llm", "embedding_model",
              "enrich", "seed")


def config_columns(run: dict[str, Any]) -> dict[str, Any]:
    config = run["config"]
    chunking = config.get("chunking") or {}
    ignored = set(config.get("ignored_axes") or ())  # the technique replaced these settings with its own
    return {**{c: NOT_APPLICABLE if c in ignored else config.get(c) for c in CONFIG_COLUMNS},
            "chunking": f"{chunking.get('strategy')}:{chunking.get('size')}/{chunking.get('overlap')}",
            "chunk_strategy": chunking.get("strategy"), "chunk_size": chunking.get("size"),
            "chunk_overlap": chunking.get("overlap"), "params": json.dumps(config.get("params") or {}, sort_keys=True),
            "technique_version": run.get("technique_version"), "config_hash": run["config_hash"],
            "index_hash": run.get("index_hash")}


def runs_of(repo: Repo, runbook_refs: list[str], only_completed: bool = True) -> list[dict[str, Any]]:
    runs = []
    for ref in runbook_refs:
        runbook = repo.get_runbook(ref)
        for run in repo.list_runs(runbook["id"]):
            if run["status"] == "completed" or not only_completed:
                runs.append({**run, "runbook_name": runbook["name"]})
    return runs


def run_table(repo: Repo, runbook_refs: list[str]) -> list[dict[str, Any]]:
    """One row per completed run: configuration + aggregated metrics (latest evaluation)."""
    rows = []
    for run in runs_of(repo, runbook_refs):
        record = repo.run_metrics(run["id"])
        metrics = dict(record["metrics"]) if record else {}
        stages = metrics.pop("latency_by_stage", {}) or {}
        rows.append({"runbook_id": run["runbook_id"], "runbook": run["runbook_name"], "run_id": run["id"],
                     "seq": run["seq"], **config_columns(run), "replicates_run_id": run["replicates_run_id"],
                     "eval_version": record["eval_version"] if record else None, **metrics,
                     **{f"latency_{stage}": seconds for stage, seconds in stages.items()}})
    return rows


def question_table(repo: Repo, runbook_refs: list[str]) -> list[dict[str, Any]]:
    """Long table: one row per run x question with configuration, efficiency and metric columns."""
    rows = []
    for run in runs_of(repo, runbook_refs):
        cols = config_columns(run)
        for result in repo.result_metrics(run["id"]):
            timings = {f"latency_{t['stage']}": t["seconds"] for t in result.pop("timings") or []}
            rows.append({"runbook_id": run["runbook_id"], "run_id": run["id"], **cols, **result, **timings})
    return rows


def answers_by_question(repo: Repo, runbook_refs: list[str]) -> list[dict[str, Any]]:
    """Side-by-side view: for each question, what every run answered, with its headline numbers."""
    questions: dict[str, dict[str, Any]] = {}
    for run in runs_of(repo, runbook_refs):
        cols = config_columns(run)
        metrics = {m["query_result_id"]: m for m in repo.result_metrics(run["id"])}
        for result in repo.query_results(run["id"]):
            entry = questions.setdefault(result["question_id"], {
                "question_id": result["question_id"], "code": result["question_code"],
                "text": result["question_text"], "answers": []})
            m = metrics.get(result["id"], {})
            entry["answers"].append({
                "result_id": result["id"], "run_id": run["id"], "seq": run["seq"], "technique": cols["technique"],
                "retrieval_mode": cols["retrieval_mode"], "reranker": cols["reranker"], "k": cols["k"],
                "chunking": cols["chunking"], "params": cols["params"], "answer": result["answer"],
                "error": result["error"], "warnings": result["warnings"], "latency_total": result["latency_total"],
                "llm_calls": result["llm_calls"], "context_chars": result["context_chars"],
                **{name: m.get(name) for name in ("recall", "mrr", "f1", "accuracy", "faithfulness",
                                                  "context_coverage", "hallucination")}})
    out = sorted(questions.values(), key=lambda q: q["code"])
    for entry in out:
        try:
            question = repo.get_question(entry["question_id"])
            entry["expected_answer"] = question["expected_answer"]
            entry["gold_passages"] = question["gold_passages"]
        except Exception:  # noqa: BLE001 - question removed after the run
            entry["expected_answer"], entry["gold_passages"] = None, []
    return out


def group_by(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Mean of each metric over the runs sharing the same value of `key` (a configuration axis)."""
    if key not in GROUP_KEYS:
        raise ValidationError(f"cannot group by '{key}' (available: {GROUP_KEYS})")
    groups: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row.get(key), []).append(row)
    names = (*MEAN_METRICS, "latency_mean", "llm_calls_per_question", "cost_usd", "context_chars_mean")
    out = []
    for value, members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        entry: dict[str, Any] = {key: value, "runs": len(members)}
        for name in names:
            values = [m[name] for m in members if m.get(name) is not None]
            entry[name] = round(statistics.fmean(values), 4) if values else None
            if len(values) > 1:
                entry[f"{name}_stdev"] = round(statistics.stdev(values), 4)
        out.append(entry)
    return out


def compare_runs(repo: Repo, run_a: str, run_b: str, seed: int = 42) -> dict[str, Any]:
    """Configuration diff plus paired statistics (b - a) on the questions both runs answered."""
    a, b = repo.get_run(run_a), repo.get_run(run_b)
    for run in (a, b):
        if run["status"] != "completed":
            raise ValidationError(f"run {run['id']} is not completed")
    ca, cb = {**config_columns(a), **{"params": a["config"].get("params")}}, \
             {**config_columns(b), **{"params": b["config"].get("params")}}
    diff = {key: {"a": ca[key], "b": cb[key]} for key in ca
            if ca[key] != cb[key] and key not in ("config_hash", "index_hash")}
    rows_a = {r["question_id"]: r for r in repo.result_metrics(a["id"]) if not r["error"]}
    rows_b = {r["question_id"]: r for r in repo.result_metrics(b["id"]) if not r["error"]}
    common = sorted(set(rows_a) & set(rows_b))
    metrics: dict[str, Any] = {}
    for name in (*MEAN_METRICS, "latency_total", "llm_calls", "prompt_tokens", "completion_tokens"):
        pairs = [(rows_a[q][name], rows_b[q][name]) for q in common
                 if rows_a[q].get(name) is not None and rows_b[q].get(name) is not None]
        if len(pairs) >= 2:
            metrics[name] = stats.paired_test([p[0] for p in pairs], [p[1] for p in pairs], seed)
    tested = [n for n in metrics if "permutation_p" in metrics[n]]
    for name, adjusted in zip(tested, stats.holm([metrics[n]["permutation_p"] for n in tested]), strict=True):
        metrics[name]["permutation_p_holm"] = adjusted
    return {"run_a": a["id"], "run_b": b["id"], "technique_a": a["technique"], "technique_b": b["technique"],
            "config_diff": diff, "common_questions": len(common), "metrics": metrics,
            "note": "differences are b - a; p-values are Holm-adjusted across the metrics tested"}
