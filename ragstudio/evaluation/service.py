"""Re-evaluation of stored runs without calling the technique again.

Metrics are recomputed from what the run persisted (answer, final context, retrieved chunks) against the current
annotations of each question, and written as a NEW eval_version: earlier versions stay untouched.
"""
from __future__ import annotations

from typing import Any

from ..config.loader import Config
from ..config.loader import load as load_config
from ..core.errors import NotFoundError, ValidationError
from ..db.repository import Repo
from ..providers.routing import resolve_endpoint
from . import evaluate_result
from .aggregate import aggregate
from .availability import availability
from .judge import Judge


def reevaluate(repo: Repo, run_ref: str, use_judge: bool | None = None, judge_model: str | None = None,
               cfg: Config | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    run = repo.get_run(run_ref)
    if run["status"] != "completed":
        raise ValidationError("only completed runs can be re-evaluated")
    config = run["config"]
    evaluation = config.get("evaluation") or {}
    judge_on = evaluation.get("judge", False) if use_judge is None else use_judge
    judge = None
    if judge_on:
        model = judge_model or evaluation.get("judge_model") or config.get("llm")
        judge = Judge(resolve_endpoint("llm", model, cfg), config.get("language", "pt"), config.get("seed"))
    version = repo.next_eval_version(run["id"])
    questions = []
    for row in repo.query_results(run["id"]):
        try:
            question = repo.get_question(row["question_id"])
        except NotFoundError:
            question = {"id": row["question_id"], "text": row["question_text"], "gold_passages": []}
        questions.append(question)
        if row["error"]:
            continue
        chunks = repo.retrieved_chunks(row["id"])
        retrieval, generation = evaluate_result(question, row["answer"], row["context_text"], chunks, judge)
        repo.add_metrics(row["id"], version, retrieval, generation)
    metrics = aggregate(repo.result_metrics(run["id"], version))
    avail = availability(questions, judge is not None)
    repo.set_run_metrics(run["id"], version, metrics, avail)
    return {"run_id": run["id"], "eval_version": version, "metrics": metrics, "availability": avail,
            "judge": judge.endpoint.model if judge else None}


def human_agreement(repo: Repo, run_ref: str) -> dict[str, Any]:
    """Agreement between human verdicts and the automatic accuracy (>= 0.5 counts as correct)."""
    run = repo.get_run(run_ref)
    reviews = repo.reviews(run["id"])
    if not reviews:
        return {"run_id": run["id"], "reviews": 0, "agreement": None,
                "note": "no human reviews yet (`evaluate review add`)"}
    metrics = {r["query_result_id"]: r for r in repo.result_metrics(run["id"])}
    compared = agree = 0
    for review in reviews:
        auto = metrics.get(review["query_result_id"], {})
        score = auto.get("judge_accuracy") if auto.get("judge_accuracy") is not None else auto.get("accuracy")
        if score is None or review["verdict"] == "partially":
            continue
        compared += 1
        agree += int((score >= 0.5) == (review["verdict"] == "correct"))
    return {"run_id": run["id"], "reviews": len(reviews), "compared": compared,
            "agreement": round(agree / compared, 4) if compared else None}
