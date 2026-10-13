"""Per-run aggregates. A metric with no measured value stays None (never 0)."""
from __future__ import annotations

import statistics
from typing import Any

MEAN_METRICS = ("hit", "recall", "precision", "mrr", "ndcg", "context_coverage", "exact_match", "f1", "accuracy",
                "faithfulness", "groundedness", "citation_accuracy", "hallucination", "refusal", "judge_accuracy",
                "judge_faithfulness")
QUADRANT_THRESHOLD = 0.7


def _values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(r[key]) for r in rows if r.get(key) is not None]


def _stats(values: list[float]) -> dict[str, Any] | None:
    if not values:
        return None
    return {"mean": round(statistics.fmean(values), 4), "median": round(statistics.median(values), 4),
            "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0, "n": len(values)}


def quadrant(accuracy: float | None, faithfulness: float | None, threshold: float = QUADRANT_THRESHOLD) -> str | None:
    if accuracy is None or faithfulness is None:
        return None
    if accuracy >= threshold and faithfulness >= threshold:
        return "Correct and grounded"
    if accuracy >= threshold:
        return "Correct but ungrounded"
    if faithfulness >= threshold:
        return "Grounded but incorrect"
    return "Incorrect and ungrounded"


def stage_latency(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, list[float]] = {}
    for row in rows:
        for timing in row.get("timings") or []:
            totals.setdefault(timing["stage"], []).append(float(timing["seconds"]))
    return {stage: round(sum(values) / len(rows), 6) for stage, values in totals.items()} if rows else {}


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """`rows`: one dict per query result with metric columns (see `Repo.result_metrics`)."""
    n = len(rows)
    out: dict[str, Any] = {"n_questions": n, "n_failed": sum(1 for r in rows if r.get("error"))}
    if not n:
        return out
    ok = [r for r in rows if not r.get("error")]
    for name in MEAN_METRICS:
        stats = _stats(_values(ok, name))
        out[name] = stats["mean"] if stats else None
        out[f"{name}_n"] = stats["n"] if stats else 0
        out[f"{name}_stdev"] = stats["stdev"] if stats else None
    latency = _stats(_values(ok, "latency_total"))
    out["latency_mean"] = latency["mean"] if latency else None
    out["latency_median"] = latency["median"] if latency else None
    out["latency_by_stage"] = stage_latency(ok)
    out["llm_calls_per_question"] = round(sum(r.get("llm_calls") or 0 for r in ok) / len(ok), 3) if ok else None
    out["prompt_tokens"] = sum(r.get("prompt_tokens") or 0 for r in ok)
    out["completion_tokens"] = sum(r.get("completion_tokens") or 0 for r in ok)
    out["embedding_tokens"] = sum(r.get("embedding_tokens") or 0 for r in ok)
    costs = [r.get("cost_usd") for r in ok]
    out["cost_usd"] = round(sum(c for c in costs if c is not None), 8) if costs and all(
        c is not None for c in costs) else None
    out["context_chars_mean"] = round(statistics.fmean(r.get("context_chars") or 0 for r in ok), 1) if ok else None
    out["quadrant"] = quadrant(out["accuracy"], out["faithfulness"])
    return out
