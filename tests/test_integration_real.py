"""Opt-in check against a REAL provider. Skipped unless RAGSTUDIO_INTEGRATION=1.

    RAGSTUDIO_INTEGRATION=1 RAGSTUDIO_INTEGRATION_PROVIDER=lmstudio \
    RAGSTUDIO_LM_STUDIO_BASE_URL=http://localhost:1234 RAGSTUDIO_LLM_MODEL=<chat model> \
    RAGSTUDIO_EMBEDDING_MODEL=<embedding model> python -m pytest tests/test_integration_real.py -q

It spends real tokens when pointed at a paid API. It checks the SHAPE of the results (same as with the mock), not
their quality.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RAGSTUDIO_INTEGRATION") != "1",
                                reason="real-provider integration test (set RAGSTUDIO_INTEGRATION=1)")
KEEP = {k: v for k, v in os.environ.items() if k.startswith("RAGSTUDIO_") and k != "RAGSTUDIO_PROVIDER"}


def test_quick_runbook_with_real_provider(populated, monkeypatch):
    from ragstudio.config.loader import load
    from ragstudio.experiments import runbook
    from ragstudio.experiments.runner import Runner
    for key, value in KEEP.items():
        if key not in ("RAGSTUDIO_DATA_DIR", "RAGSTUDIO_DB", "RAGSTUDIO_CONFIG"):
            monkeypatch.setenv(key, value)
    monkeypatch.setenv("RAGSTUDIO_PROVIDER", os.environ.get("RAGSTUDIO_INTEGRATION_PROVIDER", "lmstudio"))
    repo = populated["repo"]
    created = runbook.create(repo, {"name": "real", "corpus": "energia", "question_set": "energia-perguntas",
                                    "techniques": ["naive", "hyde", "multi_query"],
                                    "chunking": {"size": 300, "overlap": 50}, "k": 3, "limit_questions": 2}, load())
    summary = Runner(repo).execute_runbook(created["id"])
    assert summary["status"] == "completed", repo.list_runs(created["id"])
    for run in repo.list_runs(created["id"]):
        metrics = repo.run_metrics(run["id"])["metrics"]
        assert metrics["n_failed"] == 0 and metrics["prompt_tokens"] > 0 and metrics["latency_mean"] > 0
        assert repo.verify_chain(run["id"])["ok"]
