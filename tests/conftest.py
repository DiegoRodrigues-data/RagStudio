"""Shared fixtures. Every test runs offline against the mock provider, in its own temporary data tree."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("RAGSTUDIO_PROVIDER", "mock")
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Redirect data, database and local config to a temp dir; paths are resolved at call time, so this is enough."""
    monkeypatch.setenv("RAGSTUDIO_PROVIDER", "mock")
    monkeypatch.setenv("RAGSTUDIO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RAGSTUDIO_DB", str(tmp_path / "data" / "test.sqlite"))
    monkeypatch.setenv("RAGSTUDIO_CONFIG", str(tmp_path / "config.local.ini"))
    monkeypatch.delenv("RAGSTUDIO_TECHNIQUES_PATH", raising=False)
    for name in list(os.environ):
        if name.startswith("RAGSTUDIO_") and name.count("_") >= 2 and name not in (
                "RAGSTUDIO_DATA_DIR", "RAGSTUDIO_TECHNIQUES_PATH"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RAGSTUDIO_DATA_DIR", str(tmp_path / "data"))
    return tmp_path


@pytest.fixture
def documents():
    from ragstudio.ingest.loaders import load_path
    docs, _ = load_path(FIXTURES / "docs")
    return docs


@pytest.fixture
def question_file():
    return FIXTURES / "questions.json"


@pytest.fixture
def repo():
    from ragstudio.db.repository import Repo
    with Repo() as r:
        yield r


@pytest.fixture
def populated(repo, documents, question_file):
    """Corpus `energia` (3 documents) + question set `energia-perguntas` (6 questions, 4 with gold passages)."""
    from ragstudio.ingest import questions as qf
    from ragstudio.ingest.profile import corpus_profile
    from ragstudio.processing.normalize import prepare
    prepared = [prepare(d) for d in documents]
    corpus = repo.create_corpus("energia", prepared, corpus_profile([p for _, p in prepared]))
    parsed = qf.parse_file(question_file)
    qf.anchor_gold(parsed["questions"], [d for d, _ in prepared])
    qset = repo.create_question_set("energia-perguntas", language="pt")
    repo.add_questions(qset["id"], parsed["questions"])
    return {"repo": repo, "corpus": corpus, "question_set": qset}


@pytest.fixture
def store(documents):
    from ragstudio.experiments.index_builder import build_index
    from ragstudio.providers.routing import resolve_endpoint
    built, _ = build_index(documents, corpus_id="c", chunking={"strategy": "fixed", "size": 300, "overlap": 50},
                           embedder=resolve_endpoint("embedding"))
    return built


@pytest.fixture
def make_deps(store):
    """Factory of instrumented deps over the small index: make_deps(reranker="llm", retrieval_mode="hybrid")."""
    from ragstudio.experiments.deps import RunContext, build_deps
    from ragstudio.prompts import PromptSet
    from ragstudio.providers.routing import resolve_endpoint

    def factory(index=None, **overrides):
        ctx = RunContext(store=index or store, llm=resolve_endpoint("llm"), embedder=resolve_endpoint("embedding"),
                         prompts=PromptSet("pt"), **overrides)
        return build_deps(ctx)
    return factory


BASE_RUNBOOK = {"name": "t", "corpus": "energia", "question_set": "energia-perguntas",
                "chunking": {"strategy": "fixed", "size": 300, "overlap": 50}, "k": 3}


@pytest.fixture
def runbook_config():
    return json.loads(json.dumps(BASE_RUNBOOK))
