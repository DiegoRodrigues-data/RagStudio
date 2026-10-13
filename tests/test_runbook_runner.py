import json

import pytest

from ragstudio.analysis import compare
from ragstudio.config.loader import load
from ragstudio.core import registry
from ragstudio.core.errors import LeakageError, NotFoundError, RagStudioError, ValidationError
from ragstudio.evaluation import service
from ragstudio.experiments import runbook
from ragstudio.experiments.artifacts import read_results
from ragstudio.experiments.runner import Runner, reproduce


def make(repo, config, **extra):
    return runbook.create(repo, {**config, **extra}, load())


def test_grid_expansion_and_hashes(populated, runbook_config):
    cfg = load()
    raw = {**runbook_config, "techniques": ["naive", {"name": "mmr_rag", "grid": {"lambda_": [0.3, 0.9]}}],
           "k": [3, 5], "seeds": [1, 2], "retrieval_modes": ["dense", "hybrid"],
           "chunking": [{"size": 300, "overlap": 50}, {"strategy": "sentence", "size": 300, "overlap": 50}]}
    config = runbook.normalize({**raw, "prune": False}, cfg)
    runs = runbook.expand(config)
    assert len(runs) == 3 * 2 * 2 * 2 * 2 == 48 and len({r["config_hash"] for r in runs}) == 48
    assert runs == runbook.expand(runbook.normalize({**raw, "prune": False}, cfg)), "expansion must be deterministic"
    assert {json.dumps(r["config"]["params"]) for r in runs} == {"{}", '{"lambda_": 0.3}', '{"lambda_": 0.9}'}
    preview = runbook.preview(populated["repo"], raw, cfg)
    assert preview["runs"] == 32, "mmr_rag ignores the retrieval mode: 16 naive runs + 2 x 8 mmr_rag runs"
    assert preview["questions"] == 6 and preview["estimate"]["lower_bound"] is True
    assert preview["estimate"]["cost_usd"] == 0.0 and preview["duplicate_configs"] == 0


def test_pruning_drops_redundant_and_incompatible_combinations(populated, runbook_config):
    cfg = load()
    raw = {**runbook_config, "retrieval_modes": ["bm25", "dense", "rrf"], "rerankers": ["none", "lexical"],
           "enrich": [None, "contextual"],
           "chunking": [{"size": 300, "overlap": 50}, {"strategy": "parent_child", "size": 150, "overlap": 20}],
           "techniques": ["naive", "mmr_rag", "hybrid_rag", "rank_rag", "parent_child", "contextual_retrieval",
                          {"name": "rag_evo", "params": {"use_mmr": False}}, "rag_evo"]}
    runs, pruned = runbook.expand_with_report(runbook.normalize(raw, cfg))
    count = {name: sum(1 for r in runs if r["technique"] == name) for name in {r["technique"] for r in runs}}
    full = 2 * 3 * 2 * 2  # chunking x retrieval mode x reranker x enrich
    assert count["naive"] == full == 24
    assert count["mmr_rag"] == 2 * 2 == 4, "neither the retrieval mode nor the reranker changes mmr_rag"
    assert count["hybrid_rag"] == 2 * 2 * 2 == 8 and count["rank_rag"] == 2 * 3 * 2 == 12
    assert count["parent_child"] == 3 * 2 == 6, "only the parent_child chunking; the reranker is ignored"
    assert count["contextual_retrieval"] == 2 * 3 * 2 == 12, "only the enriched index"
    by_params = [r for r in runs if r["technique"] == "rag_evo"]
    assert sum(1 for r in by_params if r["config"]["params"]) == 24, "without MMR the retrieval mode matters"
    assert sum(1 for r in by_params if not r["config"]["params"]) == 8
    assert pruned["full_grid"] == 8 * full and pruned["runs"] == len(runs) == pruned["full_grid"] - pruned[
        "redundant"] - pruned["incompatible"]
    entry = {e["technique"]: e for e in pruned["by_technique"]}
    assert entry["mmr_rag"]["redundant"] == 20 and entry["mmr_rag"]["ignores"] == ["reranker", "retrieval_mode"]
    assert entry["parent_child"]["incompatible"] == 12 and "parent_child" in entry["parent_child"]["needs"][0]
    assert "naive" not in entry and pruned["without_runs"] == []
    kept = next(r["config"] for r in runs if r["technique"] == "mmr_rag")
    assert kept["retrieval_mode"] == "bm25" and kept["ignored_axes"] == ["retrieval_mode", "reranker"]
    assert len({r["config_hash"] for r in runs}) == len(runs)
    assert len(runbook.expand(runbook.normalize({**raw, "prune": False}, cfg))) == 8 * full
    with pytest.raises(ValidationError, match="no run is left after pruning"):
        runbook.preview(populated["repo"], {**runbook_config, "techniques": ["parent_child"]}, cfg)
    assert runbook.preview(populated["repo"], {**runbook_config, "techniques": "all"}, cfg)["pruned"][
        "without_runs"] == ["contextual_retrieval", "parent_child"]


def test_ignored_axes_are_shown_as_not_applicable(populated, runbook_config):
    repo = populated["repo"]
    created = make(repo, runbook_config, techniques=["naive", "mmr_rag"], retrieval_modes=["dense", "bm25"])
    assert created["runs"] == 3 and created["pruned"]["redundant"] == 1
    Runner(repo).execute_runbook(created["id"])
    rows = {(r["technique"], r["retrieval_mode"]) for r in compare.run_table(repo, [created["id"]])}
    assert rows == {("naive", "dense"), ("naive", "bm25"), ("mmr_rag", "n/a")}
    assert {r["reranker"] for r in compare.run_table(repo, [created["id"]])} == {"none", "n/a"}


def test_preset_and_all_techniques(populated, runbook_config):
    config = runbook.normalize({**runbook_config, "preset": "quick"}, load())
    assert [t["name"] for t in config["techniques"]] == ["naive", "hyde", "multi_query"] and config["k"] == [3]
    everything = runbook.normalize({**runbook_config, "techniques": "all"}, load())
    assert len(everything["techniques"]) == len(registry.all_techniques())


@pytest.mark.parametrize("patch, error, message", [
    ({"techniques": ["no_such"]}, NotFoundError, "unknown technique"),
    ({"techniques": [{"name": "naive", "params": {"bogus": 1}}]}, ValidationError, "unknown parameter"),
    ({"retrieval_modes": ["magic"]}, ValidationError, "unknown retrieval mode"),
    ({"rerankers": ["magic"]}, ValidationError, "unknown reranker"),
    ({"store": "faiss", "rerankers": ["cross_encoder"]}, ValidationError, "cannot be combined"),
    ({"chunking": {"size": 10}}, ValidationError, "at least 50"),
    ({"k": 0}, ValidationError, "k must be positive"),
    ({"corpus": ""}, ValidationError, "missing 'corpus'"),
    ({"preset": "huge"}, ValidationError, "unknown preset"),
])
def test_invalid_runbooks_are_rejected_before_running(populated, runbook_config, patch, error, message):
    with pytest.raises(error, match=message):
        runbook.preview(populated["repo"], {**runbook_config, **patch}, load())


def test_end_to_end_three_techniques(populated, runbook_config):
    repo = populated["repo"]
    events = []
    created = make(repo, runbook_config, techniques=["naive", "hyde", "rag_evo"])
    summary = Runner(repo, events.append).execute_runbook(created["id"])
    assert summary == {"runbook_id": created["id"], "status": "completed", "completed": 3, "skipped": 0,
                       "failed": 0, "cancelled": 0, "spent_usd": 0.0}
    runs = repo.list_runs(created["id"])
    assert len({r["index_hash"] for r in runs}) == 1, "same indexing configuration must share one index"
    assert [e["index_reused"] for e in events if e["event"] == "run_finished"] == [False, True, True]
    for run in runs:
        results = repo.query_results(run["id"])
        assert run["status"] == "completed" and len(results) == 6 and all(r["answer"] for r in results)
        record = repo.run_metrics(run["id"])
        metrics, avail = record["metrics"], record["availability"]
        assert metrics["n_questions"] == 6 and metrics["n_failed"] == 0
        assert metrics["recall_n"] == 4 and metrics["f1_n"] == 5 and metrics["faithfulness_n"] == 6
        assert 0 <= metrics["recall"] <= 1 and metrics["cost_usd"] == 0.0 and metrics["judge_accuracy"] is None
        assert "computed on 4 of 6" in avail["partial"]["recall"] and "judge_accuracy" in avail["requires_annotation"]
        assert repo.verify_chain(run["id"])["ok"]
        kinds = [e["kind"] for e in repo.evidence(run["id"])]
        assert kinds[0] == "info" and kinds[-1] == "info" and kinds.count("evaluation") == 6
        assert kinds.count("request") == kinds.count("response") == sum(r["llm_calls"] for r in results)
        snapshot = repo.get_snapshot(run["id"])
        assert snapshot["llm"]["provider"] == "mock" and snapshot["seed"] == 42 and snapshot["python_version"]
        artifacts = read_results(run["id"])
        assert len(artifacts) == 6 and artifacts[0]["result"]["context"]["text"]
        export = [e for e in repo.list_exports(run["id"]) if e["kind"] == "run_artifact"][0]
        assert len(export["sha256"]) == 64
        chunks = repo.retrieved_chunks(results[0]["id"])
        assert chunks and chunks[0]["rank"] == 1 and chunks[0]["text"]
    request = next(e for e in repo.evidence(runs[0]["id"]) if e["kind"] == "request")
    stored = repo.get_prompt(request["payload"]["prompt_sha256"])
    assert stored["task"] == "answer" and "{context}" in stored["template"]
    assert repo.get_runbook(created["id"])["status"] == "completed"


def test_every_technique_completes_a_runbook(populated, runbook_config):
    """The whole catalog through the runner, with one question that needs no retrieval (empty context)."""
    repo = populated["repo"]
    repo.add_questions(populated["question_set"]["id"], [{"code": "Q7", "text": "Olá?", "answer_type": "extraction"}])
    created = make(repo, runbook_config, techniques="all")
    summary = Runner(repo).execute_runbook(created["id"])
    runs = repo.list_runs(created["id"])
    without_index = {"parent_child", "contextual_retrieval"}  # pruned: this grid builds neither index they need
    assert created["pruned"]["without_runs"] == sorted(without_index)
    assert summary["status"] == "completed" and summary["completed"] == len(runs)
    assert {r["technique"] for r in runs} == set(registry.all_techniques()) - without_index
    assert len({r["index_hash"] for r in runs}) == 1
    for run in runs:
        results = repo.query_results(run["id"])
        assert len(results) == 7 and not [r for r in results if r["error"]], run["technique"]
        assert repo.verify_chain(run["id"])["ok"]
    adaptive = next(r for r in runs if r["technique"] == "adaptive_rag")
    greeting = next(r for r in repo.query_results(adaptive["id"]) if r["context_chars"] == 0)
    assert greeting["answer"] and repo.retrieved_chunks(greeting["id"]) == []
    extracting = [r["technique"] for r in runs
                  if any(e["kind"] == "request" and e["payload"]["task"] == "kg_extract" for e in repo.evidence(r["id"]))]
    assert len(extracting) == 1, "GraphRAG, LightRAG and HippoRAG share one graph extraction per index"


def test_completed_runs_are_skipped_and_interrupted_runs_restart(populated, runbook_config):
    repo = populated["repo"]
    created = make(repo, runbook_config, techniques=["naive", "hyde"])
    runner = Runner(repo)
    original = runner._answer
    calls = {"n": 0}

    def cancel_midway(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 9:  # third question of the second run
            runner.cancel()
        return original(*args, **kwargs)
    runner._answer = cancel_midway
    first = runner.execute_runbook(created["id"])
    assert first["status"] == "cancelled" and first["completed"] == 1 and first["cancelled"] == 1
    statuses = [r["status"] for r in repo.list_runs(created["id"])]
    assert statuses == ["completed", "cancelled"]
    done_before = repo.query_results(repo.list_runs(created["id"])[0]["id"])

    second = Runner(repo).execute_runbook(created["id"])
    assert second["status"] == "completed" and second["skipped"] == 1 and second["completed"] == 1
    runs = repo.list_runs(created["id"])
    assert [r["created_at"] for r in repo.query_results(runs[0]["id"])] == [r["created_at"] for r in done_before]
    assert len(repo.query_results(runs[1]["id"])) == 6 and repo.verify_chain(runs[1]["id"])["ok"]
    third = Runner(repo).execute_runbook(created["id"])
    assert third["skipped"] == 2 and third["completed"] == 0


def test_failing_technique_fails_the_run_but_not_the_runbook(populated, runbook_config, tmp_path, monkeypatch):
    (tmp_path / "boom.py").write_text(
        'from ragstudio.core.contract import TechniqueSpec\n'
        'SPEC = TechniqueSpec(name="boom", version="1", family="t", description="always fails")\n'
        'def run(request, deps):\n    raise RuntimeError("kaboom")\n', encoding="utf-8")
    (tmp_path / "flaky.py").write_text(
        'from ragstudio.techniques import naive\n'
        'from ragstudio.core.contract import TechniqueSpec\n'
        'SPEC = TechniqueSpec(name="flaky", version="1", family="t", description="fails on Itaipu")\n'
        'def run(request, deps):\n'
        '    if "Itaipu" in request.query.text:\n        raise RuntimeError("no Itaipu")\n'
        '    out = naive.run(request, deps)\n'
        '    return type(out)(**{**out.__dict__, "diagnostics": {**out.diagnostics, "technique": "flaky"}})\n',
        encoding="utf-8")
    monkeypatch.setenv("RAGSTUDIO_TECHNIQUES_PATH", str(tmp_path))
    registry.reload()
    try:
        repo = populated["repo"]
        created = make(repo, runbook_config, techniques=["boom", "flaky", "naive"])
        summary = Runner(repo).execute_runbook(created["id"])
        assert summary["status"] == "failed" and summary["failed"] == 1 and summary["completed"] == 2
        boom, flaky, naive_run = repo.list_runs(created["id"])
        assert boom["status"] == "failed" and "every question failed" in boom["error"]
        assert "kaboom" in repo.query_results(boom["id"])[0]["error"]
        assert flaky["status"] == "completed" and naive_run["status"] == "completed"
        metrics = repo.run_metrics(flaky["id"])["metrics"]
        assert metrics["n_failed"] == 1 and metrics["faithfulness_n"] == 5
        assert [e["kind"] for e in repo.evidence(flaky["id"])].count("error") == 1
    finally:
        monkeypatch.delenv("RAGSTUDIO_TECHNIQUES_PATH")
        registry.reload()


def test_split_isolation_and_leakage(populated, runbook_config):
    repo = populated["repo"]
    corpus_id, set_id = populated["corpus"]["id"], populated["question_set"]["id"]
    with pytest.raises(LeakageError, match="has no 'test' split"):
        make(repo, runbook_config, split="test")
    repo.set_splits(corpus_id, {"train": ["energia-solar"], "test": ["energia-eolica", "hidreletricas"]}, "h", 1)
    created = make(repo, runbook_config, split="test", techniques=["naive"])
    Runner(repo).execute_runbook(created["id"])
    run = repo.list_runs(created["id"])[0]
    codes = {r["question_code"] for r in repo.query_results(run["id"])}
    assert codes == {"Q1", "Q3", "Q4", "Q5", "Q6"}, "Q2 needs a train document and must be left out"
    assert repo.get_index(run["index_hash"])["documents"] == 2 and repo.get_index(run["index_hash"])["split"] == "test"
    retrieved = {c["document_id"] for r in repo.query_results(run["id"]) for c in repo.retrieved_chunks(r["id"])}
    assert "energia-solar" not in retrieved

    q2 = next(q for q in repo.list_questions(set_id) if q["code"] == "Q2")
    repo.update_question(q2["id"], {"split": "test"})
    with pytest.raises(LeakageError, match="outside it"):
        make(repo, runbook_config, split="test")
    with pytest.raises(LeakageError, match="declares no split"):
        make(repo, runbook_config)


def test_budget_is_enforced(populated, runbook_config, monkeypatch):
    from ragstudio.experiments import runner as runner_mod
    monkeypatch.setattr(runner_mod, "question_cost", lambda usage, llm, embedder: 0.01)
    repo = populated["repo"]
    created = make(repo, runbook_config, techniques=["naive", "hyde", "multi_query"], max_budget_usd=0.07)
    events = []
    summary = Runner(repo, events.append).execute_runbook(created["id"])
    assert summary["status"] == "budget_exceeded" and summary["completed"] == 2
    assert summary["spent_usd"] == pytest.approx(0.12)
    assert [r["status"] for r in repo.list_runs(created["id"])] == ["completed", "completed", "pending"]
    assert any(e["event"] == "budget_warning" for e in events)
    assert repo.get_runbook(created["id"])["status"] == "budget_exceeded"


def test_estimate_prices_known_models_and_refuses_to_guess(runbook_config):
    config = runbook.normalize({**runbook_config, "llms": ["gpt-4o", "unknown-model"]}, load())
    runs = runbook.expand(config)
    for run in runs:
        run["config"]["provider"] = "openai"
    priced = runbook.estimate(config, [runs[0]], 10)
    tokens_in = (min(6000, 3 * 300) + 400) // 4 * 10
    assert priced["prompt_tokens"] == tokens_in and priced["cost_usd"] == pytest.approx(
        (tokens_in * 2.5 + 1500 * 10.0) / 1e6, abs=1e-6)
    assert runbook.estimate(config, runs, 10)["cost_usd"] is None, "an unknown model price must not become 0"


def test_reproduce_creates_identical_replica(populated, runbook_config):
    repo = populated["repo"]
    created = make(repo, runbook_config, techniques=["multi_query"])
    Runner(repo).execute_runbook(created["id"])
    source = repo.list_runs(created["id"])[0]
    dry = reproduce(repo, source["id"], dry_run=True)
    assert dry["dry_run"] and dry["requests"] == 12 and dry["config_hash"] == source["config_hash"]
    assert len(repo.list_runs(created["id"])) == 1
    out = reproduce(repo, source["id"])
    replica = repo.get_run(out["replica_run_id"])
    assert out["identical_ratio"] == 1.0 and replica["replicates_run_id"] == source["id"]
    assert replica["config_hash"] == source["config_hash"] and replica["index_hash"] == source["index_hash"]
    with pytest.raises(RagStudioError, match="only a completed run"):
        failed = repo.add_replica_run(source["id"])
        reproduce(repo, failed["id"])


def test_reevaluation_writes_new_version(populated, runbook_config):
    repo = populated["repo"]
    created = make(repo, runbook_config, techniques=["naive"])
    Runner(repo).execute_runbook(created["id"])
    run = repo.list_runs(created["id"])[0]
    before = repo.run_metrics(run["id"])
    again = service.reevaluate(repo, run["id"], use_judge=True)
    assert again["eval_version"] == 2 and again["judge"] == "mock-llm"
    assert again["metrics"]["judge_faithfulness"] is not None and again["metrics"]["judge_accuracy_n"] == 5
    assert again["metrics"]["recall"] == before["metrics"]["recall"]
    assert repo.run_metrics(run["id"], 1)["metrics"]["judge_faithfulness"] is None, "version 1 must be untouched"
    result_id = repo.query_results(run["id"])[0]["id"]
    repo.add_review(result_id, "ana", "correct")
    agreement = service.human_agreement(repo, run["id"])
    assert agreement["reviews"] == 1 and agreement["compared"] == 1 and agreement["agreement"] in (0.0, 1.0)


def test_judge_in_runbook(populated, runbook_config):
    repo = populated["repo"]
    created = make(repo, runbook_config, techniques=["naive"], evaluation={"judge": True}, limit_questions=2)
    Runner(repo).execute_runbook(created["id"])
    record = repo.run_metrics(repo.list_runs(created["id"])[0]["id"])
    assert record["metrics"]["n_questions"] == 2 and record["metrics"]["judge_faithfulness"] is not None
    assert "judge_faithfulness" in record["availability"]["available"]


def test_missing_optional_package_is_rejected_before_any_run(populated, runbook_config, monkeypatch):
    """A reranker or store whose package is absent must fail the runbook once, not every run that uses it."""
    from ragstudio import rerankers, stores
    monkeypatch.setattr(rerankers, "missing_dependency",
                        lambda name: "sentence-transformers" if name == "cross_encoder" else None)
    with pytest.raises(ValidationError, match="pip install sentence-transformers"):
        runbook.preview(populated["repo"], {**runbook_config, "rerankers": ["none", "cross_encoder"]}, load())
    assert {"name": "cross_encoder", "available": False, "requires": "sentence-transformers"} in \
        runbook.options()["rerankers"]
    monkeypatch.setattr(stores, "missing_dependency", lambda kind: "chromadb" if kind == "chroma" else None)
    with pytest.raises(ValidationError, match="pip install chromadb"):
        runbook.preview(populated["repo"], {**runbook_config, "store": "chroma"}, load())
