import sqlite3

import pytest

from ragstudio.core.errors import NotFoundError, ValidationError
from ragstudio.db import migrate
from ragstudio.db.connection import connect

RUN = {"technique": "naive", "technique_version": "1", "config": {"k": 3}, "config_hash": "h" * 64}
QUESTION = {"id": "q_1", "code": "Q1", "text": "?"}
RESULT = {"answer": {"text": "a"}, "context": {"text": "c", "chars": 1, "truncated": False, "chunk_ids": ["d:0"]},
          "contexts": [{"chunk": {"id": "d:0", "document_id": "d", "index": 0, "char_start": 0, "char_end": 1,
                                  "text": "c"}, "score": 0.9, "source": "dense"}],
          "citations": [], "diagnostics": {}, "timings": [], "usage": {"llm_calls": 1}, "warnings": []}


def completed_run(repo):
    runbook = repo.create_runbook("rb", {"name": "rb"}, [RUN])
    run = repo.list_runs(runbook["id"])[0]
    repo.start_run(run["id"], "idx", "1")
    result_id = repo.add_query_result(run["id"], QUESTION, RESULT, 0.1, 0.0)
    for kind in ("info", "request", "response"):
        repo.add_evidence(run["id"], kind, {"kind": kind, "é": [1, 2]}, "q_1")
    repo.finish_run(run["id"], "completed", None, 0.0)
    return runbook, run, result_id


def test_migrations_are_idempotent(isolated_env):
    con = connect()
    assert migrate.migrate(con) == {"applied": [1], "version": 1}
    assert migrate.migrate(con) == {"applied": [], "version": 1}
    assert migrate.status(con) == {"version": 1, "applied": [1], "pending": []}
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"corpora", "documents", "corpus_splits", "indices", "question_sets", "questions", "gold_passages",
            "runbooks", "runs", "query_results", "retrieved_chunks", "retrieval_metrics", "generation_metrics",
            "run_metrics", "evidence_events", "prompts", "environment_snapshots", "exports", "answer_reviews"} <= tables
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    con.close()


def test_completed_run_is_immutable(repo):
    _, run, result_id = completed_run(repo)
    for sql in ("UPDATE query_results SET answer = 'x' WHERE id = ?", "DELETE FROM query_results WHERE id = ?"):
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            repo.con.execute(sql, (result_id,))
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        repo.con.execute("UPDATE retrieved_chunks SET text = 'x' WHERE query_result_id = ?", (result_id,))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repo.con.execute("UPDATE evidence_events SET payload = '{}' WHERE run_id = ?", (run["id"],))
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        repo.con.execute("DELETE FROM evidence_events WHERE run_id = ?", (run["id"],))
    with pytest.raises(sqlite3.IntegrityError, match="reconfigured"):
        repo.con.execute("UPDATE runs SET config = '{}' WHERE id = ?", (run["id"],))
    with pytest.raises(ValidationError, match="immutable"):
        repo.reset_run(run["id"])
    assert repo.query_results(run["id"])[0]["answer"] == "a"


def test_evidence_chain_detects_tampering(repo, isolated_env):
    _, run, _ = completed_run(repo)
    assert repo.verify_chain(run["id"])["ok"] and repo.verify_chain(run["id"])["events"] == 3
    raw = sqlite3.connect(repo.con.execute("PRAGMA database_list").fetchone()[2])
    raw.execute("DROP TRIGGER trg_ev_no_update")
    raw.execute("UPDATE evidence_events SET payload = replace(payload, 'request', 'tampered') WHERE seq = 2")
    raw.commit()
    raw.close()
    assert repo.verify_chain(run["id"]) == {"ok": False, "events": 3, "broken_at_seq": 2}


def test_evidence_chain_detects_removed_event(repo):
    _, run, _ = completed_run(repo)
    raw = sqlite3.connect(repo.con.execute("PRAGMA database_list").fetchone()[2])
    raw.execute("DROP TRIGGER trg_ev_no_delete")
    raw.execute("DELETE FROM evidence_events WHERE seq = 2")
    raw.commit()
    raw.close()
    assert repo.verify_chain(run["id"])["broken_at_seq"] == 3


def test_metrics_are_append_only_versions(repo):
    _, run, result_id = completed_run(repo)
    retrieval = {"k": 1, "gold_count": 1, "hit": 1.0, "recall": 1.0, "precision": 1.0, "mrr": 1.0, "ndcg": 1.0,
                 "context_coverage": 1.0}
    assert repo.next_eval_version(run["id"]) == 1
    repo.add_metrics(result_id, 1, retrieval, {"f1": 0.5})
    repo.set_run_metrics(run["id"], 1, {"f1": 0.5}, {})
    repo.add_metrics(result_id, 2, {**retrieval, "recall": 0.0}, {"f1": 0.9})
    repo.set_run_metrics(run["id"], 2, {"f1": 0.9}, {})
    assert repo.next_eval_version(run["id"]) == 3
    assert repo.run_metrics(run["id"])["metrics"] == {"f1": 0.9}
    assert repo.run_metrics(run["id"], 1)["metrics"] == {"f1": 0.5}
    assert repo.result_metrics(run["id"])[0]["recall"] == 0.0 and repo.result_metrics(run["id"], 1)[0]["recall"] == 1.0
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repo.con.execute("UPDATE generation_metrics SET f1 = 1")


def test_guarded_delete_requires_exact_name_and_backs_up(repo, isolated_env):
    runbook, run, _ = completed_run(repo)
    assert repo.delete_preview(runbook["id"])["evidence_events"] == 3
    with pytest.raises(ValidationError, match="does not match"):
        repo.delete_runbook(runbook["id"], "wrong")
    out = repo.delete_runbook(runbook["id"], "rb")
    assert out["deleted"] and out["query_results"] == 1
    assert list((isolated_env / "data" / "backups").glob("auto_*.sqlite"))
    with pytest.raises(NotFoundError):
        repo.get_runbook(runbook["id"])
    assert repo.counts()["evidence_events"] == 0
    assert repo.con.execute("SELECT value FROM maintenance").fetchone()[0] == "0"


def test_question_versioning(populated):
    repo = populated["repo"]
    question = repo.list_questions(populated["question_set"]["id"])[0]
    edited = repo.update_question(question["id"], {"text": "novo texto"})
    assert edited["version"] == 1 and edited["supersedes_id"] is None and edited["gold_passages"]
    runbook = repo.create_runbook("rb", {}, [RUN])
    run = repo.list_runs(runbook["id"])[0]
    repo.start_run(run["id"], "idx", "1")
    repo.add_query_result(run["id"], {"id": edited["id"], "code": edited["code"], "text": edited["text"]}, RESULT,
                          0.1, None)
    repo.finish_run(run["id"], "completed")
    newer = repo.update_question(edited["id"], {"expected_answer": "outra"})
    assert newer["version"] == 2 and newer["supersedes_id"] == edited["id"] and newer["id"] != edited["id"]
    active = repo.list_questions(populated["question_set"]["id"])
    assert len(active) == 6 and newer["id"] in {q["id"] for q in active}
    assert len(repo.list_questions(populated["question_set"]["id"], include_archived=True)) == 7
    assert repo.get_question(edited["id"])["archived_at"]


def test_corpus_and_lookup_rules(populated):
    repo = populated["repo"]
    assert repo.get_corpus("energia")["id"] == populated["corpus"]["id"] == repo.get_corpus(
        populated["corpus"]["id"][:6])["id"]
    assert [d.id for d in repo.corpus_documents(populated["corpus"]["id"], ["energia-solar"])] == ["energia-solar"]
    with pytest.raises(ValidationError, match="already exists"):
        repo.create_corpus("energia", [], {})
    with pytest.raises(ValidationError, match="already in this set"):
        repo.add_questions(populated["question_set"]["id"], [{"code": "Q1", "text": "dup"}])
    assert repo.integrity_check()["ok"]
