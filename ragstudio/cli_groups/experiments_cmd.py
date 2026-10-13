"""`ragstudio experiments ...`: runbooks (grids of runs), execution, status, reproduction, guarded deletion."""
from __future__ import annotations

import argparse
from typing import Any

from ..config.loader import load
from ..core.errors import ValidationError
from ..db.repository import Repo
from ..experiments import runbook as runbook_mod
from ..experiments.artifacts import read_results
from ..experiments.runner import Runner, reproduce
from .common import command, json_value, progress_printer


def _raw(args: argparse.Namespace) -> dict[str, Any]:
    if bool(args.config) == bool(args.file):
        raise ValidationError("give exactly one of --config '<json>' or --file runbook.yaml")
    raw = runbook_mod.load_file(args.file) if args.file else json_value(args.config, "--config")
    if not isinstance(raw, dict):
        raise ValidationError("the runbook configuration must be a JSON/YAML mapping")
    return raw


def _preview(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return runbook_mod.preview(repo, _raw(args), load())


def _create(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return runbook_mod.create(repo, _raw(args), load())


def _run(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        runbook_id = args.id or runbook_mod.create(repo, _raw(args), load())["id"]
        return Runner(repo, progress_printer(args.stream)).execute_runbook(runbook_id)


def _list(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return repo.list_runbooks()


def _status(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        runbook = repo.get_runbook(args.id)
        runs = []
        for run in repo.list_runs(runbook["id"]):
            record = repo.run_metrics(run["id"])
            metrics = record["metrics"] if record else {}
            runs.append({"id": run["id"], "seq": run["seq"], "technique": run["technique"], "status": run["status"],
                         "error": run["error"], "cost_usd": run["cost_usd"], "config_hash": run["config_hash"][:16],
                         "replicates_run_id": run["replicates_run_id"],
                         **{k: metrics.get(k) for k in ("recall", "mrr", "f1", "faithfulness", "latency_mean",
                                                        "llm_calls_per_question")}})
        return {"id": runbook["id"], "name": runbook["name"], "status": runbook["status"],
                "estimate": runbook["estimate"], "max_budget_usd": runbook["max_budget_usd"], "runs": runs}


def _show(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        run = repo.get_run(args.run_id)
        results = repo.query_results(run["id"])
        record = repo.run_metrics(run["id"])
        out: dict[str, Any] = {"run": {k: run[k] for k in ("id", "technique", "technique_version", "status", "error",
                                                           "config", "config_hash", "index_hash", "cost_usd",
                                                           "started_at", "finished_at")},
                               "metrics": record["metrics"] if record else None,
                               "availability": record["availability"] if record else None,
                               "environment": repo.get_snapshot(run["id"]),
                               "evidence": repo.verify_chain(run["id"]),
                               "answers": [{"id": r["id"], "question": r["question_code"],
                                            "text": r["question_text"], "answer": r["answer"],
                                            "latency": r["latency_total"], "llm_calls": r["llm_calls"],
                                            "warnings": r["warnings"], "error": r["error"]} for r in results]}
        if args.full:
            out["artifacts"] = read_results(run["id"])
        return out


def _answer(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        result = repo.get_query_result(args.result_id)
        run = repo.get_run(result["run_id"])
        try:
            question = repo.get_question(result["question_id"])
        except Exception:  # noqa: BLE001 - question removed after the run
            question = None
        metrics = next((m for m in repo.result_metrics(run["id"]) if m["query_result_id"] == result["id"]), None)
        return {"result": result, "chunks": repo.retrieved_chunks(result["id"]), "metrics": metrics,
                "question": question, "run": {"id": run["id"], "technique": run["technique"],
                                              "config": run["config"], "status": run["status"]}}


def _evidence(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        run = repo.get_run(args.run_id)
        events = repo.evidence(run["id"])
        if args.question_id:
            events = [e for e in events if e["question_id"] == args.question_id]
        total = len(events)
        return {"run_id": run["id"], "total": total, "chain": repo.verify_chain(run["id"]),
                "events": events[args.offset:args.offset + args.limit]}


def _reproduce(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return reproduce(repo, args.run_id, args.dry_run, progress_printer(args.stream))


def _verify(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        runbook = repo.get_runbook(args.id)
        chains = {run["id"]: repo.verify_chain(run["id"]) for run in repo.list_runs(runbook["id"])}
        return {"runbook": runbook["id"], "ok": all(c["ok"] for c in chains.values()), "runs": chains}


def _delete_preview(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return repo.delete_preview(args.id)


def _delete(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return repo.delete_runbook(args.id, args.confirm)


def _presets(args: argparse.Namespace) -> Any:
    return runbook_mod.PRESETS


def _options(args: argparse.Namespace) -> Any:
    return runbook_mod.options()


def register(groups: Any) -> None:
    sub = groups.add_parser("experiments", help="runbooks and runs").add_subparsers(dest="command", required=True)
    for name, handler, text in (("preview", _preview, "expand a runbook and estimate it without saving"),
                                ("create", _create, "save a runbook (grid of pending runs)")):
        p = command(sub, name, handler, text)
        p.add_argument("--config", help="inline JSON or @file")
        p.add_argument("--file", help="runbook .yaml / .json")
    p = command(sub, "run", _run, "execute a runbook; completed runs are skipped, interrupted ones restart")
    p.add_argument("--id", help="existing runbook id (or unique prefix / name)")
    p.add_argument("--config")
    p.add_argument("--file", help="create the runbook from this file and run it")
    p.add_argument("--stream", action="store_true", help="print progress events as JSON lines")
    command(sub, "list", _list, "runbooks")
    command(sub, "status", _status, "runs of a runbook with headline metrics").add_argument("--id", required=True)
    p = command(sub, "show", _show, "one run: configuration, metrics, environment, answers")
    p.add_argument("--run-id", required=True)
    p.add_argument("--full", action="store_true", help="include the JSONL artifacts (contexts, diagnostics)")
    command(sub, "answer", _answer, "one answer: context chunks, metrics, question and gold").add_argument(
        "--result-id", type=int, required=True)
    p = command(sub, "evidence", _evidence, "evidence events of a run (paged) and chain verification")
    p.add_argument("--run-id", required=True)
    p.add_argument("--question-id")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=200)
    p = command(sub, "reproduce", _reproduce, "re-execute a completed run as a linked replica")
    p.add_argument("--run-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--stream", action="store_true")
    command(sub, "verify", _verify, "recompute the evidence hash chain of every run").add_argument("--id",
                                                                                                   required=True)
    command(sub, "delete-preview", _delete_preview, "what a deletion would remove").add_argument("--id",
                                                                                                required=True)
    p = command(sub, "delete", _delete, "delete a runbook and its results (backs the database up first)")
    p.add_argument("--id", required=True)
    p.add_argument("--confirm", required=True, help="exact runbook name")
    command(sub, "presets", _presets, "built-in runbook presets")
    command(sub, "options", _options, "rerankers and stores, with the package each one still needs")
