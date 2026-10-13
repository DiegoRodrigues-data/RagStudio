"""`ragstudio compare ...`: techniques side by side, paired statistics, document characteristics."""
from __future__ import annotations

import argparse
from typing import Any

from ..analysis import characteristics, compare
from ..db.repository import Repo
from .common import command, csv_list


def _runs(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        a, b = csv_list(args.ids)[:2]
        return compare.compare_runs(repo, a, b, args.seed)


def _runbook(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        rows = compare.run_table(repo, csv_list(args.id))
        return {"by": args.by, "groups": compare.group_by(rows, args.by), "runs": len(rows)}


def _table(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        refs = csv_list(args.id)
        rows = compare.run_table(repo, refs) if args.kind == "runs" else compare.question_table(repo, refs)
        return {"kind": args.kind, "rows": rows}


def _answers(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return compare.answers_by_question(repo, csv_list(args.id))


def _characteristics(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return characteristics.analyze(repo, csv_list(args.runbook_id))


def register(groups: Any) -> None:
    sub = groups.add_parser("compare", help="comparison and empirical analysis").add_subparsers(dest="command",
                                                                                                required=True)
    p = command(sub, "runs", _runs, "paired comparison of two runs (b - a) with tests and effect size")
    p.add_argument("--ids", required=True, help="run_a,run_b")
    p.add_argument("--seed", type=int, default=42)
    p = command(sub, "runbook", _runbook, "mean metrics grouped by a configuration axis")
    p.add_argument("--id", required=True, help="runbook id(s), comma separated")
    p.add_argument("--by", default="technique", choices=compare.GROUP_KEYS)
    p = command(sub, "table", _table, "full table: one row per run, or per run x question")
    p.add_argument("--id", required=True, help="runbook id(s), comma separated")
    p.add_argument("--kind", default="runs", choices=("runs", "questions"))
    command(sub, "answers", _answers, "every question with the answer of each run side by side").add_argument(
        "--id", required=True)
    command(sub, "characteristics", _characteristics,
            "metrics crossed with document and corpus characteristics").add_argument("--runbook-id", required=True)
