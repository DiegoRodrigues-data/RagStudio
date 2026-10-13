import json

from ragstudio.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    return code, json.loads(lines[-1]), [json.loads(line) for line in lines[:-1]]


def test_unknown_group_is_usage_error(capsys):
    code, payload, _ = run(capsys, "nope")
    assert code == 2 and payload["ok"] is False and payload["error_type"] == "UsageError"


def test_handled_error_keeps_contract(capsys):
    code, payload, _ = run(capsys, "corpus", "describe", "--name", "missing")
    assert code == 1 and payload == {"ok": False, "error": "corpus 'missing' not found",
                                     "error_type": "NotFoundError", "warnings": []}


def test_db_migrate_and_status(capsys):
    code, payload, _ = run(capsys, "db", "migrate")
    assert code == 0 and payload["ok"] and payload["data"]["version"] == 1
    code, payload, _ = run(capsys, "db", "status")
    assert payload["data"]["pending"] == [] and payload["data"]["counts"]["runs"] == 0


def test_techniques_list_reports_status(capsys):
    code, payload, _ = run(capsys, "techniques", "list")
    names = {t["name"]: t["status"] for t in payload["data"]}
    assert code == 0 and names["naive"] == "implemented" and names["self_rag"] == "prototype"
    titles = {t["name"]: t["title"] for t in payload["data"]}
    assert titles["naive"] == "Naive RAG" and titles["corrective"] == "Corrective RAG" and all(titles.values())


def test_full_flow_through_cli(capsys, question_file, tmp_path):
    fixtures = question_file.parent
    assert run(capsys, "corpus", "import", "--path", str(fixtures / "docs"), "--name", "energia")[1]["ok"]
    code, payload, _ = run(capsys, "questions", "import-json", "--path", str(question_file), "--corpus", "energia")
    assert payload["data"] == {"id": payload["data"]["id"], "name": "energia-perguntas", "questions": 6,
                               "with_gold_passages": 4, "with_expected_answer": 5}
    config = json.dumps({"name": "cli", "corpus": "energia", "question_set": "energia-perguntas",
                         "techniques": ["naive", "hyde"], "chunking": {"size": 300, "overlap": 50}, "k": 3})
    code, payload, progress = run(capsys, "experiments", "run", "--config", config, "--stream")
    assert code == 0 and payload["data"]["status"] == "completed" and payload["data"]["completed"] == 2
    assert [p["progress"]["event"] for p in progress][0] == "runbook_started"
    assert sum(1 for p in progress if p["progress"]["event"] == "question_done") == 12
    runbook_id = payload["data"]["runbook_id"]
    code, payload, _ = run(capsys, "compare", "runbook", "--id", runbook_id)
    assert {g["technique"] for g in payload["data"]["groups"]} == {"naive", "hyde"}
    out = tmp_path / "report.html"
    code, payload, _ = run(capsys, "reports", "html", "--runbook-ids", runbook_id, "--output", str(out))
    assert code == 0 and out.is_file() and "Mock provider" in out.read_text(encoding="utf-8")
    code, payload, _ = run(capsys, "experiments", "verify", "--id", runbook_id)
    assert payload["data"]["ok"] is True


def test_commands_used_by_the_desktop_app(capsys, question_file):
    fixtures = question_file.parent
    run(capsys, "corpus", "import", "--path", str(fixtures / "docs"), "--name", "energia")
    run(capsys, "questions", "import-json", "--path", str(question_file), "--corpus", "energia")
    code, payload, _ = run(capsys, "corpus", "document", "--name", "energia", "--doc-id", "energia-solar")
    assert payload["data"]["text"].startswith("# Energia solar") and payload["data"]["profile"]["language"] == "pt"
    code, payload, _ = run(capsys, "config", "set-many", "--json",
                           json.dumps({"llm": {"model": "m1", "temperature": 0.2}, "experiments": {"k": 7}}))
    assert payload["data"]["changed"] == 3 and payload["data"]["config"]["experiments"]["k"] == "7"
    assert run(capsys, "config", "set-many", "--json", '{"llm": {"bogus": 1}}')[1]["ok"] is False
    options = run(capsys, "experiments", "options")[1]["data"]
    assert [o["name"] for o in options["rerankers"]] == ["none", "lexical", "llm", "cross_encoder"]
    assert {"name": "memory", "available": True, "requires": None} in options["stores"]
    catalog = run(capsys, "reference", "list", "--language", "en")[1]["data"]
    assert {"guide", "technique", "component", "metric", "statistic", "concept"} == {e["kind"] for e in catalog["entries"]}
    assert all(key in catalog["sources"] for e in catalog["entries"] for key in e["sources"])
    assert run(capsys, "reference", "show", "--id", "metric.nope")[1]["error_type"] == "NotFoundError"
    config = json.dumps({"name": "ui", "corpus": "energia", "question_set": "energia-perguntas",
                         "techniques": ["naive", "hyde"], "chunking": {"size": 300, "overlap": 50}, "k": 3})
    runbook_id = run(capsys, "experiments", "run", "--config", config)[1]["data"]["runbook_id"]
    code, payload, _ = run(capsys, "compare", "table", "--id", runbook_id)
    rows = payload["data"]["rows"]
    assert len(rows) == 2 and {"run_id", "technique", "recall", "latency_mean"} <= set(rows[0])
    assert len(run(capsys, "compare", "table", "--id", runbook_id, "--kind", "questions")[1]["data"]["rows"]) == 12
    code, payload, _ = run(capsys, "compare", "answers", "--id", runbook_id)
    first = payload["data"][0]
    assert len(payload["data"]) == 6 and first["code"] == "Q1" and len(first["answers"]) == 2
    assert first["expected_answer"] and first["gold_passages"] and first["answers"][0]["answer"]
    result_id = first["answers"][0]["result_id"]
    code, payload, _ = run(capsys, "experiments", "answer", "--result-id", str(result_id))
    detail = payload["data"]
    assert detail["chunks"] and detail["metrics"]["recall"] is not None and detail["question"]["code"] == "Q1"
    code, payload, _ = run(capsys, "experiments", "evidence", "--run-id", detail["run"]["id"], "--limit", "5")
    assert payload["data"]["chain"]["ok"] and len(payload["data"]["events"]) == 5 and payload["data"]["total"] > 5
    question_id = detail["question"]["id"]
    scoped = run(capsys, "experiments", "evidence", "--run-id", detail["run"]["id"], "--question-id", question_id)
    assert {e["question_id"] for e in scoped[1]["data"]["events"]} == {question_id}
    code, payload, _ = run(capsys, "questions", "archive", "--id", question_id)
    assert payload["data"]["archived_at"]
    assert len(run(capsys, "questions", "list", "--set", "energia-perguntas")[1]["data"]["questions"]) == 5
