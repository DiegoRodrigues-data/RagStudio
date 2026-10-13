"""`ragstudio evaluate ...`: metric availability, re-evaluation from stored artifacts, human reviews."""
from __future__ import annotations

import argparse
from typing import Any

from ..db.repository import Repo
from ..evaluation import service
from ..evaluation.availability import availability
from .common import command


def _availability(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        qset = repo.get_question_set(args.question_set)
        return {"question_set": qset["name"], **availability(repo.list_questions(qset["id"]), args.judge)}


def _rerun(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        judge = True if args.judge else False if args.no_judge else None
        return service.reevaluate(repo, args.run_id, judge, args.judge_model)


def _metrics(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        run = repo.get_run(args.run_id)
        return {"run_id": run["id"], "aggregate": repo.run_metrics(run["id"], args.eval_version),
                "questions": repo.result_metrics(run["id"], args.eval_version)}


def _review_add(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return {"id": repo.add_review(args.result_id, args.reviewer, args.verdict, args.note or "")}


def _agreement(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return service.human_agreement(repo, args.run_id)


def register(groups: Any) -> None:
    sub = groups.add_parser("evaluate", help="metrics and reviews").add_subparsers(dest="command", required=True)
    p = command(sub, "availability", _availability, "which metrics a question set allows and which need annotation")
    p.add_argument("--question-set", required=True)
    p.add_argument("--judge", action="store_true")
    p = command(sub, "rerun", _rerun, "recompute metrics from stored results as a new evaluation version")
    p.add_argument("--run-id", required=True)
    p.add_argument("--judge", action="store_true")
    p.add_argument("--no-judge", action="store_true")
    p.add_argument("--judge-model")
    p = command(sub, "metrics", _metrics, "aggregate and per-question metrics of a run")
    p.add_argument("--run-id", required=True)
    p.add_argument("--eval-version", type=int)
    p = command(sub, "review-add", _review_add, "record a human verdict for one answer")
    p.add_argument("--result-id", type=int, required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--verdict", required=True, choices=("correct", "partially", "incorrect"))
    p.add_argument("--note")
    command(sub, "agreement", _agreement, "agreement between human verdicts and automatic accuracy").add_argument(
        "--run-id", required=True)
