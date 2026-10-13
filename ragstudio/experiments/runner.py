"""Experiment runner: executes every run of a runbook through the same contract and persists everything.

For each run: resolve data (split + leakage check) -> build or reuse the index -> environment snapshot -> for each
question: build instrumented deps -> technique.run -> validate -> persist result, chunks, evidence, metrics and
the JSONL artifact -> aggregate. Completed runs are never executed again (use `reproduce` for a replica).
"""
from __future__ import annotations

import signal
import time
from collections.abc import Callable
from typing import Any

from ..config.loader import Config
from ..config.loader import load as load_config
from ..core import registry
from ..core.contract import TechniqueRequest, validate_result
from ..core.errors import BudgetExceeded, RagStudioError
from ..core.logging import get_logger, log
from ..core.models import GoldPassage, Query
from ..core.seeds import set_global_seed
from ..db.repository import Repo
from ..evaluation import evaluate_result
from ..evaluation.aggregate import aggregate
from ..evaluation.availability import availability
from ..evaluation.judge import Judge
from ..prompts import PromptSet
from ..providers import cost as pricing
from ..providers.base import Endpoint
from ..providers.cache import EmbeddingCache
from ..providers.fingerprint import model_fingerprint
from ..providers.routing import resolve_endpoint
from . import runbook as runbook_mod
from .artifacts import ResultWriter
from .deps import Recorder, RunContext, build_deps
from .environment import snapshot
from .index_builder import build_index

Progress = Callable[[dict[str, Any]], None]
BUDGET_WARNING = 0.8


class Cancelled(Exception):
    pass


def to_query(question: dict[str, Any]) -> Query:
    gold = tuple(GoldPassage(g["document_id"], g["text"], g.get("char_start"), g.get("char_end"))
                 for g in question.get("gold_passages") or [])
    return Query(id=question["id"], text=question["text"], expected_answer=question.get("expected_answer"),
                 gold_passages=gold, answer_type=question.get("answer_type") or "extraction",
                 split=question.get("split"), metadata=question.get("metadata") or {})


def question_cost(usage: dict[str, Any], llm: Endpoint, embedder: Endpoint) -> float | None:
    return pricing.total_cost(
        pricing.llm_cost(llm.model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), llm.is_local),
        pricing.embedding_cost(embedder.model, usage.get("embedding_tokens", 0), embedder.is_local))


def chunk_rows(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"document_id": c["chunk"]["document_id"], "char_start": c["chunk"]["char_start"],
             "char_end": c["chunk"]["char_end"], "text": c["chunk"]["text"]} for c in contexts]


class Runner:
    def __init__(self, repo: Repo, progress: Progress | None = None, cfg: Config | None = None) -> None:
        self.repo = repo
        self.cfg = cfg or load_config()
        self._progress = progress
        self._cancel = False
        self.logger = get_logger("ragstudio.runner")

    # ---------------------------------------------------------------- control
    def cancel(self) -> None:
        self._cancel = True

    def _install_signals(self) -> None:
        try:
            signal.signal(signal.SIGTERM, lambda *_: self.cancel())
            signal.signal(signal.SIGINT, lambda *_: self.cancel())
        except ValueError:  # not in the main thread (tests, embedding in another app)
            pass

    def _emit(self, event: dict[str, Any]) -> None:
        if self._progress:
            self._progress(event)

    def _check_cancel(self) -> None:
        if self._cancel:
            raise Cancelled()

    # ---------------------------------------------------------------- runbook
    def execute_runbook(self, runbook_ref: str, only_run_ids: list[str] | None = None) -> dict[str, Any]:
        runbook = self.repo.get_runbook(runbook_ref)
        runs = self.repo.list_runs(runbook["id"])
        if only_run_ids:
            runs = [r for r in runs if r["id"] in only_run_ids]
        budget = runbook["max_budget_usd"]
        spent = sum(r["cost_usd"] or 0.0 for r in self.repo.list_runs(runbook["id"]) if r["status"] == "completed")
        self._install_signals()
        self.repo.set_runbook_status(runbook["id"], "running")
        self._emit({"event": "runbook_started", "runbook_id": runbook["id"], "runs": len(runs)})
        summary = {"completed": 0, "skipped": 0, "failed": 0, "cancelled": 0}
        warned = False
        outcome = "completed"
        try:
            for position, run in enumerate(runs, 1):
                if run["status"] == "completed":
                    summary["skipped"] += 1
                    self._emit({"event": "run_skipped", "run_id": run["id"], "reason": "already completed"})
                    continue
                self._check_cancel()
                if budget is not None and spent >= budget:
                    raise BudgetExceeded(f"budget ${budget:.4f} reached (spent ${spent:.4f})")
                if run["status"] != "pending":
                    self.repo.reset_run(run["id"])  # partial results of a failed/cancelled/interrupted run
                self._emit({"event": "run_started", "run_id": run["id"], "technique": run["technique"],
                            "position": position, "of": len(runs)})
                result = self.execute_run(self.repo.get_run(run["id"]))
                summary[result["status"]] += 1
                spent += result.get("cost_usd") or 0.0
                self._emit({"event": "run_finished", "run_id": run["id"], **result, "spent_usd": round(spent, 6)})
                if budget and not warned and spent >= budget * BUDGET_WARNING:
                    warned = True
                    self._emit({"event": "budget_warning", "spent_usd": round(spent, 6), "budget_usd": budget})
                if result["status"] == "cancelled":
                    raise Cancelled()
        except Cancelled:
            outcome = "cancelled"
        except BudgetExceeded as exc:
            outcome = "budget_exceeded"
            self.repo.log("warning", str(exc), runbook_id=runbook["id"])
        else:
            statuses = {r["status"] for r in self.repo.list_runs(runbook["id"])}
            outcome = "completed" if statuses == {"completed"} else "failed" if "failed" in statuses else "pending"
        self.repo.set_runbook_status(runbook["id"], outcome)
        final = {"runbook_id": runbook["id"], "status": outcome, **summary, "spent_usd": round(spent, 6)}
        self._emit({"event": "runbook_finished", **final})
        return final

    # -------------------------------------------------------------------- run
    def execute_run(self, run: dict[str, Any]) -> dict[str, Any]:
        run_id = run["id"]
        try:
            return self._execute(run)
        except Cancelled:
            self.repo.finish_run(run_id, "cancelled", "cancelled by signal")
            return {"status": "cancelled"}
        except Exception as exc:  # noqa: BLE001 - a run failure must never abort the remaining runs
            message = f"{type(exc).__name__}: {exc}"
            log(self.logger, "error", "run failed", run_id=run_id, error=message)
            if self.repo.get_run(run_id)["status"] == "running":
                self.repo.add_evidence(run_id, "error", {"stage": "run", "error": message})
            self.repo.finish_run(run_id, "failed", message)
            self.repo.log("error", message, run_id=run_id, runbook_id=run["runbook_id"])
            return {"status": "failed", "error": message}

    def _execute(self, run: dict[str, Any]) -> dict[str, Any]:
        run_id, config = run["id"], run["config"]
        technique = registry.get(config["technique"])
        params = technique.spec.resolve(config.get("params"))
        data = runbook_mod.resolve_data(self.repo, config)
        questions = data["questions"]
        llm = resolve_endpoint("llm", config.get("llm"), self.cfg)
        embedder = resolve_endpoint("embedding", config.get("embedding_model"), self.cfg)

        store, reused = build_index(
            data["documents"], corpus_id=data["corpus"]["id"], chunking=config["chunking"], embedder=embedder,
            store=config["store"], split=config.get("split"), enrich=config.get("enrich"), llm=llm,
            language=config["language"], batch_size=self.cfg.get_int("embedding", "batch_size", 32),
            timeout=self.cfg.get_int("provider", "timeout_embedding", 60),
            progress=lambda e: self._emit({"run_id": run_id, **e}))
        self.repo.register_index(store.meta.to_dict(), str(store.path))
        self.repo.start_run(run_id, store.meta.index_hash, technique.spec.version)
        seed = int(config["seed"])
        set_global_seed(seed)
        fingerprint = model_fingerprint(llm, self.cfg.get_bool("experiments", "fingerprint_probe"), seed)
        self.repo.add_snapshot(run_id, snapshot(fingerprint, embedder.public(), seed))
        self.repo.add_evidence(run_id, "info", {
            "event": "run_started", "technique": technique.spec.name, "technique_version": technique.spec.version,
            "config_hash": run["config_hash"], "index_hash": store.meta.index_hash, "index_reused": reused,
            "questions": len(questions), "documents": len(data["documents"]), "params": params})

        prompts = PromptSet(config["language"])
        cache = EmbeddingCache()
        ctx = RunContext(
            store=store, llm=llm, embedder=embedder, prompts=prompts, retrieval_mode=config["retrieval_mode"],
            retrieval_options=config.get("retrieval_options") or {}, reranker=config.get("reranker") or "none",
            temperature=config["temperature"], max_tokens=config["max_tokens"], seed=seed,
            timeout_llm=self.cfg.get_int("provider", "timeout_llm", 120),
            timeout_embedding=self.cfg.get_int("provider", "timeout_embedding", 60),
            max_retries=self.cfg.get_int("provider", "max_retries", 4), cache=cache)
        judge = self._judge(config, llm, seed)
        writer = ResultWriter(run_id)
        failed = 0
        total_cost: float | None = 0.0
        try:
            for position, question in enumerate(questions, 1):
                self._check_cancel()
                outcome = self._answer(run_id, technique, question, config, params, ctx, llm, embedder, judge, writer)
                failed += int(outcome["failed"])
                total_cost = None if total_cost is None or outcome["cost_usd"] is None \
                    else total_cost + outcome["cost_usd"]
                self._emit({"event": "question_done", "run_id": run_id, "question": question["code"],
                            "position": position, "of": len(questions), "failed": outcome["failed"],
                            "latency": outcome["latency"]})
        finally:
            cache.close()
            artifact_path, artifact_sha = writer.close()

        if failed == len(questions):
            raise RagStudioError(f"every question failed ({failed}/{len(questions)}); see evidence events")
        metrics = aggregate(self.repo.result_metrics(run_id, 1))
        avail = availability(questions, judge is not None)
        self.repo.set_run_metrics(run_id, 1, metrics, avail)
        self.repo.add_export("run_artifact", run_id, "jsonl", artifact_path, artifact_sha)
        self.repo.add_evidence(run_id, "info", {"event": "run_finished", "questions": len(questions),
                                                "failed": failed, "artifact_sha256": artifact_sha,
                                                "cost_usd": total_cost})
        self.repo.finish_run(run_id, "completed", None, round(total_cost, 8) if total_cost is not None else None)
        return {"status": "completed", "questions": len(questions), "failed_questions": failed,
                "cost_usd": total_cost, "index_reused": reused, "index_hash": store.meta.index_hash}

    def _judge(self, config: dict[str, Any], llm: Endpoint, seed: int) -> Judge | None:
        evaluation = config.get("evaluation") or {}
        if not evaluation.get("judge"):
            return None
        endpoint = resolve_endpoint("llm", evaluation.get("judge_model"), self.cfg) \
            if evaluation.get("judge_model") else llm
        return Judge(endpoint, config["language"], seed, self.cfg.get_int("provider", "timeout_llm", 120))

    def _answer(self, run_id: str, technique: registry.Technique, question: dict[str, Any], config: dict[str, Any],
                params: dict[str, Any], ctx: RunContext, llm: Endpoint, embedder: Endpoint, judge: Judge | None,
                writer: ResultWriter) -> dict[str, Any]:
        recorder = Recorder()
        deps, _ = build_deps(ctx, recorder)
        request = TechniqueRequest(query=to_query(question), k=int(config["k"]),
                                   max_context_chars=int(config["max_context_chars"]), params=params)
        started = time.perf_counter()
        error: str | None = None
        try:
            payload = validate_result(technique.run(request, deps), technique.spec).to_dict()
        except Cancelled:
            raise
        except Exception as exc:  # noqa: BLE001 - one failed question is recorded and the run goes on
            error = f"{type(exc).__name__}: {exc}"
            payload = {"answer": {"text": ""}, "contexts": [], "context": {}, "citations": [], "diagnostics": {},
                       "timings": [t.to_dict() for t in deps.timings()], "usage": recorder.usage().to_dict(),
                       "warnings": []}
        latency = round(time.perf_counter() - started, 6)
        cost = question_cost(payload["usage"], llm, embedder)
        result_id = self.repo.add_query_result(run_id, question, payload, latency, cost, error)
        for sha, prompt in recorder.prompts.items():
            self.repo.upsert_prompt(sha, prompt["task"], ctx.prompts.language, prompt["system"], prompt["template"],
                                    ctx.prompts.version)
        for event in recorder.events:
            self.repo.add_evidence(run_id, event["kind"], event["payload"], question["id"])
        retrieval = generation = None
        if error:
            self.repo.add_evidence(run_id, "error", {"question": question["code"], "error": error}, question["id"])
        else:
            retrieval, generation = evaluate_result(question, payload["answer"]["text"], payload["context"]["text"],
                                                    chunk_rows(payload["contexts"]), judge)
            self.repo.add_metrics(result_id, 1, retrieval, generation)
            self.repo.add_evidence(run_id, "evaluation", {"query_result_id": result_id, "eval_version": 1,
                                                          "retrieval": retrieval, "generation": generation},
                                   question["id"])
        writer.write({"query_result_id": result_id, "question": {k: question[k] for k in (
            "id", "code", "text", "expected_answer", "answer_type", "gold_passages")}, "result": payload,
            "latency_total": latency, "cost_usd": cost, "error": error,
            "metrics": {"retrieval": retrieval, "generation": generation}})
        return {"failed": bool(error), "cost_usd": cost, "latency": latency}


def reproduce(repo: Repo, run_ref: str, dry_run: bool = False, progress: Progress | None = None) -> dict[str, Any]:
    """Re-execute the exact configuration of a completed run as a replica linked by `replicates_run_id`.

    `dry_run` only shows what would be sent: the configuration and the recorded requests."""
    source = repo.get_run(run_ref)
    if source["status"] != "completed":
        raise RagStudioError("only a completed run can be reproduced")
    if dry_run:
        requests = [e["payload"] for e in repo.evidence(source["id"]) if e["kind"] == "request"]
        return {"dry_run": True, "run_id": source["id"], "config": source["config"],
                "config_hash": source["config_hash"], "requests": len(requests), "sample_requests": requests[:3],
                "environment": repo.get_snapshot(source["id"])}
    replica = repo.add_replica_run(source["id"])
    outcome = Runner(repo, progress).execute_run(replica)
    original = {r["question_id"]: r["answer"] for r in repo.query_results(source["id"])}
    again = {r["question_id"]: r["answer"] for r in repo.query_results(replica["id"])}
    same = sum(1 for qid, answer in original.items() if again.get(qid) == answer)
    return {"dry_run": False, "source_run_id": source["id"], "replica_run_id": replica["id"], **outcome,
            "identical_answers": same, "questions": len(original),
            "identical_ratio": round(same / len(original), 4) if original else None}
