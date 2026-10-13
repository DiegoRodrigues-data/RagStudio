"""Repository: ALL SQL lives here. Every other module talks to SQLite through `Repo`.

Opening a `Repo` applies pending migrations. JSON columns are decoded on read and encoded on write.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.errors import NotFoundError, ValidationError
from ..core.hashing import canonical_json, sha256_json, sha256_text
from ..core.models import Document
from . import backup as backup_mod
from .connection import connect, transaction
from .migrate import migrate

JSON_COLUMNS = {"cleaning", "profile", "metadata", "document_ids", "chunking", "chunking_profile", "build_usage",
                "config", "estimate", "citations", "diagnostics", "timings", "usage", "warnings", "metrics",
                "availability", "packages", "llm", "embedder", "payload"}
RUN_STATUSES = ("pending", "running", "completed", "failed", "cancelled")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    out = dict(row)
    for key in out.keys() & JSON_COLUMNS:
        if isinstance(out[key], str):
            try:
                out[key] = json.loads(out[key])
            except json.JSONDecodeError:
                pass
    return out


class Repo:
    def __init__(self, path: Path | None = None) -> None:
        self.con = connect(path)
        migrate(self.con)

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> Repo:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _all(self, sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
        return [_row(r) for r in self.con.execute(sql, params).fetchall()]  # type: ignore[misc]

    def _one(self, sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
        return _row(self.con.execute(sql, params).fetchone())

    def _resolve(self, table: str, ref: str, label: str, by_name: bool = True) -> dict[str, Any]:
        """Find a row by exact id, exact name, or unique id prefix."""
        row = self._one(f"SELECT * FROM {table} WHERE id = ?", (ref,))
        if row is None and by_name:
            row = self._one(f"SELECT * FROM {table} WHERE name = ?", (ref,))
        if row is None:
            rows = self._all(f"SELECT * FROM {table} WHERE id LIKE ?", (ref + "%",))
            if len(rows) > 1:
                raise ValidationError(f"{label} reference '{ref}' is ambiguous ({len(rows)} matches)")
            row = rows[0] if rows else None
        if row is None:
            raise NotFoundError(f"{label} '{ref}' not found")
        return row

    # ================================================================ database
    def integrity_check(self) -> dict[str, Any]:
        result = [r[0] for r in self.con.execute("PRAGMA integrity_check").fetchall()]
        fk = [tuple(r) for r in self.con.execute("PRAGMA foreign_key_check").fetchall()]
        return {"ok": result == ["ok"] and not fk, "integrity": result, "foreign_key_violations": len(fk)}

    def vacuum(self) -> None:
        self.con.execute("VACUUM")

    def backup(self, output: Path | None = None) -> str:
        return str(backup_mod.backup(self.con, output))

    def counts(self) -> dict[str, int]:
        tables = ("corpora", "documents", "indices", "question_sets", "questions", "runbooks", "runs",
                  "query_results", "evidence_events")
        return {t: self.con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}

    # ================================================================== corpus
    def create_corpus(self, name: str, documents: list[tuple[Document, dict[str, Any]]], profile: dict[str, Any],
                      description: str = "", source_path: str = "", cleaning: list[str] | None = None) -> dict[str, Any]:
        if self._one("SELECT id FROM corpora WHERE name = ?", (name,)):
            raise ValidationError(f"corpus '{name}' already exists")
        corpus_id = new_id("cp")
        content_hash = sha256_json(sorted((d.id, d.sha256) for d, _ in documents))
        languages = profile.get("languages", {})
        language = max(languages, key=languages.get) if languages else ""
        with transaction(self.con):
            self.con.execute("INSERT INTO corpora VALUES (?,?,?,?,?,?,?,?,?)",
                             (corpus_id, name, description, language, source_path, content_hash,
                              _dump(cleaning or []), _dump(profile), now()))
            self.con.executemany(
                "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(corpus_id, d.id, d.source_path, d.sha256, d.format, d.language, d.chars, d.pages, d.text,
                  _dump(d.metadata), _dump(p)) for d, p in documents])
        return self.get_corpus(corpus_id)

    def get_corpus(self, ref: str) -> dict[str, Any]:
        return self._resolve("corpora", ref, "corpus")

    def list_corpora(self) -> list[dict[str, Any]]:
        return self._all("SELECT c.*, (SELECT COUNT(*) FROM documents d WHERE d.corpus_id = c.id) AS documents "
                         "FROM corpora c ORDER BY c.created_at")

    def document_rows(self, corpus_id: str, with_text: bool = False) -> list[dict[str, Any]]:
        cols = "*" if with_text else ("corpus_id, doc_id, source_path, sha256, format, language, chars, pages, "
                                      "metadata, profile")
        return self._all(f"SELECT {cols} FROM documents WHERE corpus_id = ? ORDER BY doc_id", (corpus_id,))

    def corpus_documents(self, corpus_id: str, only: list[str] | None = None) -> list[Document]:
        rows = self.document_rows(corpus_id, with_text=True)
        wanted = set(only) if only is not None else None
        return [Document(id=r["doc_id"], text=r["text"], source_path=r["source_path"], sha256=r["sha256"],
                         format=r["format"], language=r["language"], chars=r["chars"], pages=r["pages"],
                         metadata=r["metadata"]) for r in rows if wanted is None or r["doc_id"] in wanted]

    def get_document(self, corpus_id: str, doc_id: str) -> dict[str, Any]:
        row = self._one("SELECT * FROM documents WHERE corpus_id = ? AND doc_id = ?", (corpus_id, doc_id))
        if row is None:
            raise NotFoundError(f"document '{doc_id}' not found in this corpus")
        return row

    def delete_corpus(self, corpus_id: str) -> None:
        if self._one("SELECT 1 FROM indices WHERE corpus_id = ?", (corpus_id,)):
            raise ValidationError("this corpus has indices; delete them first (`index delete`)")
        with transaction(self.con):
            self.con.execute("DELETE FROM corpora WHERE id = ?", (corpus_id,))

    def set_splits(self, corpus_id: str, splits: dict[str, list[str]], split_hash: str, seed: int | None) -> None:
        with transaction(self.con):
            self.con.execute("DELETE FROM corpus_splits WHERE corpus_id = ?", (corpus_id,))
            self.con.executemany("INSERT INTO corpus_splits VALUES (?,?,?,?,?,?)",
                                 [(corpus_id, name, _dump(sorted(ids)), split_hash, seed, now())
                                  for name, ids in splits.items()])

    def get_splits(self, corpus_id: str) -> dict[str, list[str]]:
        rows = self._all("SELECT split, document_ids FROM corpus_splits WHERE corpus_id = ?", (corpus_id,))
        return {r["split"]: r["document_ids"] for r in rows}

    # ================================================================= indices
    def register_index(self, meta: dict[str, Any], path: str) -> None:
        with transaction(self.con):
            self.con.execute(
                "INSERT OR REPLACE INTO indices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (meta["index_hash"], meta["corpus_id"], meta.get("split"), _dump(meta["chunking"]),
                 meta["embedding_model"], meta.get("embedding_provider", ""), meta.get("store", "memory"),
                 meta.get("enrich"), meta.get("dim", 0), meta.get("chunks", 0), meta.get("documents", 0), path,
                 _dump(meta.get("chunking_profile", {})), _dump(meta.get("build_usage", {})),
                 meta.get("created_at") or now()))

    def list_indices(self, corpus_id: str | None = None) -> list[dict[str, Any]]:
        if corpus_id:
            return self._all("SELECT * FROM indices WHERE corpus_id = ? ORDER BY created_at", (corpus_id,))
        return self._all("SELECT * FROM indices ORDER BY created_at")

    def get_index(self, ref: str) -> dict[str, Any]:
        rows = self._all("SELECT * FROM indices WHERE index_hash LIKE ?", (ref + "%",))
        if len(rows) != 1:
            raise NotFoundError(f"index '{ref}' not found" if not rows else f"index '{ref}' is ambiguous")
        return rows[0]

    def delete_index(self, index_hash: str) -> None:
        if self._one("SELECT 1 FROM runs WHERE index_hash = ? AND status = 'completed'", (index_hash,)):
            raise ValidationError("this index was used by completed runs; it is kept so they stay reproducible")
        with transaction(self.con):
            self.con.execute("DELETE FROM indices WHERE index_hash = ?", (index_hash,))

    # =============================================================== questions
    def create_question_set(self, name: str, description: str = "", language: str = "") -> dict[str, Any]:
        if self._one("SELECT id FROM question_sets WHERE name = ?", (name,)):
            raise ValidationError(f"question set '{name}' already exists")
        set_id = new_id("qs")
        with transaction(self.con):
            self.con.execute("INSERT INTO question_sets VALUES (?,?,?,?,?)",
                             (set_id, name, description, language, now()))
        return self.get_question_set(set_id)

    def get_question_set(self, ref: str) -> dict[str, Any]:
        return self._resolve("question_sets", ref, "question set")

    def list_question_sets(self) -> list[dict[str, Any]]:
        return self._all(
            "SELECT s.*, (SELECT COUNT(*) FROM questions q WHERE q.set_id = s.id AND q.archived_at IS NULL) "
            "AS questions FROM question_sets s ORDER BY s.created_at")

    def _insert_question(self, set_id: str, q: dict[str, Any], version: int = 1,
                         supersedes: str | None = None) -> str:
        question_id = new_id("q")
        self.con.execute(
            "INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (question_id, set_id, q["code"], q["text"], q.get("expected_answer"),
             q.get("answer_type") or "extraction", q.get("split"), _dump(q.get("metadata") or {}), version,
             supersedes, None, now()))
        for gold in q.get("gold_passages") or []:
            self.con.execute(
                "INSERT INTO gold_passages (question_id, document_id, text, char_start, char_end, source) "
                "VALUES (?,?,?,?,?,?)",
                (question_id, gold["document_id"], gold["text"], gold.get("char_start"), gold.get("char_end"),
                 gold.get("source") or "imported"))
        return question_id

    def add_questions(self, set_id: str, questions: list[dict[str, Any]]) -> list[str]:
        codes = [q["code"] for q in questions]
        if len(set(codes)) != len(codes):
            raise ValidationError("duplicate question codes in the same set")
        existing = {r["code"] for r in self._all(
            "SELECT code FROM questions WHERE set_id = ? AND archived_at IS NULL", (set_id,))}
        clash = sorted(existing & set(codes))
        if clash:
            raise ValidationError(f"question code(s) already in this set: {clash}")
        with transaction(self.con):
            return [self._insert_question(set_id, q) for q in questions]

    def list_questions(self, set_id: str, include_archived: bool = False) -> list[dict[str, Any]]:
        where = "" if include_archived else "AND archived_at IS NULL"
        rows = self._all(f"SELECT * FROM questions WHERE set_id = ? {where} ORDER BY code, version", (set_id,))
        for row in rows:
            row["gold_passages"] = self._all(
                "SELECT document_id, text, char_start, char_end, source FROM gold_passages WHERE question_id = ? "
                "ORDER BY id", (row["id"],))
        return rows

    def get_question(self, question_id: str) -> dict[str, Any]:
        row = self._one("SELECT * FROM questions WHERE id = ?", (question_id,))
        if row is None:
            raise NotFoundError(f"question '{question_id}' not found")
        row["gold_passages"] = self._all(
            "SELECT document_id, text, char_start, char_end, source FROM gold_passages WHERE question_id = ? "
            "ORDER BY id", (question_id,))
        return row

    def question_used(self, question_id: str) -> bool:
        return self._one("SELECT 1 FROM query_results q JOIN runs r ON r.id = q.run_id "
                         "WHERE q.question_id = ? AND r.status = 'completed'", (question_id,)) is not None

    def update_question(self, question_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Edits in place while unused; once a completed run used it, creates a new version and archives the old."""
        current = self.get_question(question_id)
        merged = {**current, **{k: v for k, v in changes.items() if v is not None}}
        with transaction(self.con):
            if self.question_used(question_id):
                self.con.execute("UPDATE questions SET archived_at = ? WHERE id = ?", (now(), question_id))
                new = self._insert_question(current["set_id"], merged, current["version"] + 1, question_id)
            else:
                self.con.execute("DELETE FROM questions WHERE id = ?", (question_id,))
                new = self._insert_question(current["set_id"], merged, current["version"], current["supersedes_id"])
        return self.get_question(new)

    def archive_question(self, question_id: str) -> dict[str, Any]:
        self.get_question(question_id)
        with transaction(self.con):
            self.con.execute("UPDATE questions SET archived_at = COALESCE(archived_at, ?) WHERE id = ?",
                             (now(), question_id))
        return self.get_question(question_id)

    # ================================================================ runbooks
    def create_runbook(self, name: str, config: dict[str, Any], runs: list[dict[str, Any]],
                       estimate: dict[str, Any] | None = None, description: str = "",
                       max_budget_usd: float | None = None) -> dict[str, Any]:
        runbook_id = new_id("rb")
        with transaction(self.con):
            self.con.execute(
                "INSERT INTO runbooks (id, name, description, config, status, max_budget_usd, estimate, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (runbook_id, name, description, _dump(config), "pending", max_budget_usd, _dump(estimate or {}),
                 now()))
            for seq, run in enumerate(runs, 1):
                self.con.execute(
                    "INSERT INTO runs (id, runbook_id, seq, technique, technique_version, config, config_hash, "
                    "status) VALUES (?,?,?,?,?,?,?,?)",
                    (new_id("run"), runbook_id, seq, run["technique"], run.get("technique_version", ""),
                     _dump(run["config"]), run["config_hash"], "pending"))
        return self.get_runbook(runbook_id)

    def get_runbook(self, ref: str) -> dict[str, Any]:
        return self._resolve("runbooks", ref, "runbook")

    def list_runbooks(self) -> list[dict[str, Any]]:
        return self._all(
            "SELECT b.id, b.name, b.description, b.status, b.max_budget_usd, b.created_at, b.started_at, "
            "b.finished_at, (SELECT COUNT(*) FROM runs r WHERE r.runbook_id = b.id) AS runs, "
            "(SELECT COUNT(*) FROM runs r WHERE r.runbook_id = b.id AND r.status = 'completed') AS completed, "
            "(SELECT SUM(r.cost_usd) FROM runs r WHERE r.runbook_id = b.id) AS cost_usd "
            "FROM runbooks b ORDER BY b.created_at")

    def set_runbook_status(self, runbook_id: str, status: str) -> None:
        stamp = now()
        with transaction(self.con):
            if status == "running":
                self.con.execute("UPDATE runbooks SET status = ?, started_at = COALESCE(started_at, ?), "
                                 "finished_at = NULL WHERE id = ?", (status, stamp, runbook_id))
            else:
                self.con.execute("UPDATE runbooks SET status = ?, finished_at = ? WHERE id = ?",
                                 (status, stamp, runbook_id))

    def list_runs(self, runbook_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM runs WHERE runbook_id = ? ORDER BY seq", (runbook_id,))

    def get_run(self, ref: str) -> dict[str, Any]:
        return self._resolve("runs", ref, "run", by_name=False)

    def start_run(self, run_id: str, index_hash: str, technique_version: str) -> None:
        with transaction(self.con):
            self.con.execute("UPDATE runs SET status = 'running', index_hash = ?, technique_version = ?, "
                             "error = NULL, started_at = ?, finished_at = NULL WHERE id = ?",
                             (index_hash, technique_version, now(), run_id))

    def finish_run(self, run_id: str, status: str, error: str | None = None, cost_usd: float | None = None) -> None:
        if status not in RUN_STATUSES:
            raise ValidationError(f"invalid run status '{status}'")
        with transaction(self.con):
            self.con.execute("UPDATE runs SET status = ?, error = ?, cost_usd = ?, finished_at = ? WHERE id = ?",
                             (status, error, cost_usd, now(), run_id))

    def reset_run(self, run_id: str) -> None:
        """Drop partial results of a run that did not complete, so it can be executed again from scratch."""
        run = self.get_run(run_id)
        if run["status"] == "completed":
            raise ValidationError("a completed run is immutable; use `experiments reproduce` to run it again")
        with transaction(self.con):
            self.con.execute("DELETE FROM query_results WHERE run_id = ?", (run_id,))
            self.con.execute("DELETE FROM evidence_events WHERE run_id = ?", (run_id,))
            self.con.execute("DELETE FROM environment_snapshots WHERE run_id = ?", (run_id,))
            self.con.execute("DELETE FROM run_metrics WHERE run_id = ?", (run_id,))
            self.con.execute("UPDATE runs SET status = 'pending', error = NULL, cost_usd = NULL, started_at = NULL, "
                             "finished_at = NULL WHERE id = ?", (run_id,))

    def add_replica_run(self, run_id: str) -> dict[str, Any]:
        source = self.get_run(run_id)
        seq = self.con.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM runs WHERE runbook_id = ?",
                               (source["runbook_id"],)).fetchone()[0]
        replica = new_id("run")
        with transaction(self.con):
            self.con.execute(
                "INSERT INTO runs (id, runbook_id, seq, technique, technique_version, config, config_hash, status, "
                "replicates_run_id) VALUES (?,?,?,?,?,?,?,?,?)",
                (replica, source["runbook_id"], seq, source["technique"], source["technique_version"],
                 _dump(source["config"]), source["config_hash"], "pending", source["id"]))
        return self.get_run(replica)

    # ================================================================= results
    def add_query_result(self, run_id: str, question: dict[str, Any], result: dict[str, Any], latency_total: float,
                         cost_usd: float | None, error: str | None = None) -> int:
        usage = result.get("usage", {})
        context = result.get("context", {})
        with transaction(self.con):
            cur = self.con.execute(
                "INSERT INTO query_results (run_id, question_id, question_code, question_text, answer, context_text, "
                "context_chars, context_truncated, citations, diagnostics, timings, usage, latency_total, llm_calls, "
                "prompt_tokens, completion_tokens, embedding_tokens, cost_usd, warnings, error, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, question["id"], question["code"], question["text"],
                 result.get("answer", {}).get("text", ""), context.get("text", ""), context.get("chars", 0),
                 int(bool(context.get("truncated"))), _dump(result.get("citations", [])),
                 _dump(result.get("diagnostics", {})), _dump(result.get("timings", [])), _dump(usage),
                 latency_total, usage.get("llm_calls", 0), usage.get("prompt_tokens", 0),
                 usage.get("completion_tokens", 0), usage.get("embedding_tokens", 0), cost_usd,
                 _dump(result.get("warnings", [])), error, now()))
            result_id = int(cur.lastrowid or 0)
            in_context = set(context.get("chunk_ids", []))
            self.con.executemany(
                "INSERT INTO retrieved_chunks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(result_id, rank, c["chunk"]["id"], c["chunk"]["document_id"], c["chunk"]["index"], c["score"],
                  c["source"], c["chunk"]["char_start"], c["chunk"]["char_end"], int(c["chunk"]["id"] in in_context),
                  c["chunk"]["text"]) for rank, c in enumerate(result.get("contexts", []), 1)])
        return result_id

    def query_results(self, run_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM query_results WHERE run_id = ? ORDER BY question_code, id", (run_id,))

    def get_query_result(self, result_id: int) -> dict[str, Any]:
        row = self._one("SELECT * FROM query_results WHERE id = ?", (result_id,))
        if row is None:
            raise NotFoundError(f"query result {result_id} not found")
        return row

    def retrieved_chunks(self, result_id: int) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM retrieved_chunks WHERE query_result_id = ? ORDER BY rank", (result_id,))

    def done_question_ids(self, run_id: str) -> set[str]:
        return {r["question_id"] for r in self._all("SELECT question_id FROM query_results WHERE run_id = ?",
                                                    (run_id,))}

    # ================================================================= metrics
    def next_eval_version(self, run_id: str) -> int:
        row = self.con.execute("SELECT COALESCE(MAX(eval_version), 0) + 1 FROM run_metrics WHERE run_id = ?",
                               (run_id,)).fetchone()
        return int(row[0])

    def add_metrics(self, result_id: int, eval_version: int, retrieval: dict[str, Any] | None,
                    generation: dict[str, Any] | None) -> None:
        with transaction(self.con):
            if retrieval is not None:
                self.con.execute(
                    "INSERT INTO retrieval_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (result_id, eval_version, retrieval["k"], retrieval["gold_count"], retrieval.get("hit"),
                     retrieval.get("recall"), retrieval.get("precision"), retrieval.get("mrr"), retrieval.get("ndcg"),
                     retrieval.get("context_coverage"), now()))
            if generation is not None:
                g = generation
                self.con.execute(
                    "INSERT INTO generation_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (result_id, eval_version, g.get("exact_match"), g.get("f1"), g.get("accuracy"),
                     g.get("faithfulness"), g.get("groundedness"), g.get("citation_accuracy"),
                     g.get("hallucination"), g.get("refusal"), g.get("judge_accuracy"), g.get("judge_faithfulness"),
                     g.get("judge_model"), g.get("judge_prompt_sha256"), now()))

    def set_run_metrics(self, run_id: str, eval_version: int, metrics: dict[str, Any],
                        availability: dict[str, Any]) -> None:
        with transaction(self.con):
            self.con.execute("INSERT INTO run_metrics VALUES (?,?,?,?,?)",
                             (run_id, eval_version, _dump(metrics), _dump(availability), now()))

    def run_metrics(self, run_id: str, eval_version: int | None = None) -> dict[str, Any] | None:
        if eval_version is None:
            return self._one("SELECT * FROM run_metrics WHERE run_id = ? ORDER BY eval_version DESC LIMIT 1",
                             (run_id,))
        return self._one("SELECT * FROM run_metrics WHERE run_id = ? AND eval_version = ?", (run_id, eval_version))

    def result_metrics(self, run_id: str, eval_version: int | None = None) -> list[dict[str, Any]]:
        """One row per query result with the latest (or given) retrieval and generation metrics joined."""
        version = eval_version or self.con.execute(
            "SELECT COALESCE(MAX(eval_version), 0) FROM run_metrics WHERE run_id = ?", (run_id,)).fetchone()[0]
        return self._all(
            "SELECT q.id AS query_result_id, q.run_id, q.question_id, q.question_code, q.latency_total, "
            "q.llm_calls, q.prompt_tokens, q.completion_tokens, q.embedding_tokens, q.cost_usd, q.context_chars, "
            "q.timings, q.error, rm.k, rm.gold_count, rm.hit, rm.recall, rm.precision, rm.mrr, rm.ndcg, "
            "rm.context_coverage, gm.exact_match, gm.f1, gm.accuracy, gm.faithfulness, gm.groundedness, "
            "gm.citation_accuracy, gm.hallucination, gm.refusal, gm.judge_accuracy, gm.judge_faithfulness "
            "FROM query_results q "
            "LEFT JOIN retrieval_metrics rm ON rm.query_result_id = q.id AND rm.eval_version = ? "
            "LEFT JOIN generation_metrics gm ON gm.query_result_id = q.id AND gm.eval_version = ? "
            "WHERE q.run_id = ? ORDER BY q.question_code", (version, version, run_id))

    def add_review(self, result_id: int, reviewer: str, verdict: str, note: str = "") -> int:
        self.get_query_result(result_id)
        with transaction(self.con):
            cur = self.con.execute("INSERT INTO answer_reviews (query_result_id, reviewer, verdict, note, created_at) "
                                   "VALUES (?,?,?,?,?)", (result_id, reviewer, verdict, note, now()))
        return int(cur.lastrowid or 0)

    def reviews(self, run_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT a.* FROM answer_reviews a JOIN query_results q ON q.id = a.query_result_id "
                         "WHERE q.run_id = ? ORDER BY a.id", (run_id,))

    # ================================================================ evidence
    def add_evidence(self, run_id: str, kind: str, payload: dict[str, Any], question_id: str | None = None) -> int:
        """Append one event to the run's hash chain: chain = sha256(previous chain + sha256(canonical payload))."""
        text = canonical_json(payload)
        payload_sha = sha256_text(text)
        with transaction(self.con):
            last = self.con.execute("SELECT seq, chain_sha256 FROM evidence_events WHERE run_id = ? "
                                    "ORDER BY seq DESC LIMIT 1", (run_id,)).fetchone()
            seq, prev = (last["seq"] + 1, last["chain_sha256"]) if last else (1, "")
            self.con.execute(
                "INSERT INTO evidence_events (run_id, seq, kind, question_id, payload, payload_sha256, prev_sha256, "
                "chain_sha256, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (run_id, seq, kind, question_id, text, payload_sha, prev, sha256_text(prev + payload_sha), now()))
        return seq

    def evidence(self, run_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM evidence_events WHERE run_id = ? ORDER BY seq", (run_id,))

    def verify_chain(self, run_id: str) -> dict[str, Any]:
        """Recompute the chain from the stored payloads, re-canonicalizing each one."""
        prev = ""
        rows = self.con.execute("SELECT seq, payload, payload_sha256, prev_sha256, chain_sha256 FROM evidence_events "
                                "WHERE run_id = ? ORDER BY seq", (run_id,)).fetchall()
        expected_seq = 1
        for row in rows:
            payload_sha = sha256_text(canonical_json(json.loads(row["payload"])))
            broken = (row["seq"] != expected_seq or payload_sha != row["payload_sha256"]
                      or row["prev_sha256"] != prev or sha256_text(prev + payload_sha) != row["chain_sha256"])
            if broken:
                return {"ok": False, "events": len(rows), "broken_at_seq": row["seq"]}
            prev = row["chain_sha256"]
            expected_seq += 1
        return {"ok": True, "events": len(rows), "head": prev}

    def upsert_prompt(self, sha256: str, task: str, language: str, system: str, template: str, version: str) -> None:
        self.con.execute("INSERT OR IGNORE INTO prompts VALUES (?,?,?,?,?,?,?)",
                         (sha256, task, language, system, template, version, now()))

    def get_prompt(self, sha256: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM prompts WHERE sha256 = ?", (sha256,))

    def add_snapshot(self, run_id: str, snapshot: dict[str, Any]) -> None:
        with transaction(self.con):
            self.con.execute(
                "INSERT OR REPLACE INTO environment_snapshots VALUES (?,?,?,?,?,?,?,?,?,?)",
                (run_id, snapshot["python_version"], snapshot["platform"], _dump(snapshot["packages"]),
                 snapshot.get("git_commit"), snapshot["ragstudio_version"], _dump(snapshot["llm"]),
                 _dump(snapshot["embedder"]), snapshot.get("seed"), now()))

    def get_snapshot(self, run_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM environment_snapshots WHERE run_id = ?", (run_id,))

    def add_export(self, kind: str, ref: str, fmt: str, path: str, sha256: str) -> None:
        with transaction(self.con):
            self.con.execute("INSERT INTO exports (kind, ref, format, path, sha256, created_at) VALUES (?,?,?,?,?,?)",
                             (kind, ref, fmt, path, sha256, now()))

    def list_exports(self, ref: str | None = None) -> list[dict[str, Any]]:
        if ref:
            return self._all("SELECT * FROM exports WHERE ref LIKE ? ORDER BY id", (f"%{ref}%",))
        return self._all("SELECT * FROM exports ORDER BY id")

    def log(self, level: str, message: str, run_id: str | None = None, runbook_id: str | None = None) -> None:
        self.con.execute("INSERT INTO run_logs (run_id, runbook_id, level, message, created_at) VALUES (?,?,?,?,?)",
                         (run_id, runbook_id, level, message, now()))

    def logs(self, runbook_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM run_logs WHERE runbook_id = ? ORDER BY id DESC LIMIT ?", (runbook_id, limit))

    # ========================================================= guarded deletion
    def delete_preview(self, runbook_id: str) -> dict[str, Any]:
        rb = self.get_runbook(runbook_id)
        count = lambda sql: self.con.execute(sql, (rb["id"],)).fetchone()[0]  # noqa: E731
        return {"runbook": rb["name"], "id": rb["id"], "status": rb["status"],
                "runs": count("SELECT COUNT(*) FROM runs WHERE runbook_id = ?"),
                "query_results": count("SELECT COUNT(*) FROM query_results q JOIN runs r ON r.id = q.run_id "
                                       "WHERE r.runbook_id = ?"),
                "evidence_events": count("SELECT COUNT(*) FROM evidence_events e JOIN runs r ON r.id = e.run_id "
                                         "WHERE r.runbook_id = ?")}

    def delete_runbook(self, runbook_id: str, confirm: str) -> dict[str, Any]:
        """Deletes a runbook and everything it produced. Requires the exact runbook name; backs up first."""
        rb = self.get_runbook(runbook_id)
        if confirm != rb["name"]:
            raise ValidationError(f"confirmation does not match the runbook name ('{rb['name']}')")
        if rb["status"] == "running":
            raise ValidationError("the runbook is running; cancel it first")
        preview = self.delete_preview(rb["id"])
        saved = backup_mod.backup(self.con, auto=True)
        with transaction(self.con):
            self.con.execute("UPDATE maintenance SET value = '1' WHERE key = 'allow_delete'")
            self.con.execute("DELETE FROM runbooks WHERE id = ?", (rb["id"],))
            self.con.execute("UPDATE maintenance SET value = '0' WHERE key = 'allow_delete'")
        return {**preview, "deleted": True, "backup": str(saved)}
