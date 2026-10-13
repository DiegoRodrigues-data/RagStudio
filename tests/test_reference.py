"""The reference catalog must stay complete and consistent with the code it documents."""
from __future__ import annotations

import pytest

from ragstudio import reference
from ragstudio.core import registry
from ragstudio.evaluation.aggregate import MEAN_METRICS
from ragstudio.processing.chunking import STRATEGIES
from ragstudio.reference import techniques
from ragstudio.reference.entry import KINDS, SECTIONS
from ragstudio.reference.sources import SOURCES
from ragstudio.rerankers import REQUIRES as RERANKER_REQUIRES
from ragstudio.retrieval import MODES
from ragstudio.stores import KINDS as STORE_KINDS
from ragstudio.stores import REQUIRES as STORE_REQUIRES


@pytest.fixture(scope="module")
def raw():
    return reference.raw_entries()


def test_every_registered_technique_is_explained_in_both_languages(raw):
    entries = {e["id"]: e for e in raw[0]}
    for name, technique in registry.all_techniques().items():
        entry = entries[f"technique.{name}"]
        assert name in techniques.TEXT, f"add '{name}' to ragstudio/reference/techniques.py"
        assert technique.spec.family in techniques.FAMILIES and technique.spec.stage in reference.STAGES
        assert entry["facts"]["ignores"] == list(technique.spec.ignored_axes())
        assert entry["facts"]["status"] == technique.spec.status
        assert [p["name"] for p in entry["facts"]["params"]] == list(technique.spec.params)
        assert entry["sources"], f"technique '{name}' cites nothing"
    assert set(techniques.TEXT) <= set(registry.all_techniques())


def test_every_metric_the_app_shows_has_an_entry(raw):
    documented = {key for e in raw[0] if e["kind"] == "metric" for key in e["facts"]["keys"]}
    efficiency = {"latency_mean", "llm_calls_per_question", "prompt_tokens", "completion_tokens", "embedding_tokens",
                  "cost_usd", "context_chars_mean"}
    assert not (set(MEAN_METRICS) | efficiency) - documented
    for e in raw[0]:
        if e["kind"] == "metric":
            assert e["facts"]["needs"] in {"none", "gold", "expected", "judge", "judge+expected", "human"}
            assert e["facts"]["better"] in {"higher", "lower", "context"}
            assert e["facts"]["range"] in {"unit", "binary", "seconds", "count", "usd", "chars"}


def test_every_runbook_option_has_a_component_entry(raw):
    ids = {e["id"] for e in raw[0]}
    expected = ([f"component.retrieval.{m}" for m in MODES] + [f"component.chunking.{s}" for s in STRATEGIES]
                + [f"component.store.{s}" for s in STORE_KINDS]
                + [f"component.reranker.{r}" for r in ("none", "lexical", "llm", "cross_encoder")])
    assert not [i for i in expected if i not in ids]
    entries = {e["id"]: e for e in raw[0]}
    for kind, requires in (("store", STORE_REQUIRES), ("reranker", RERANKER_REQUIRES)):
        for name, (_, package) in requires.items():
            assert entries[f"component.{kind}.{name}"]["facts"]["package"] == package


def test_entries_are_consistent(raw):
    entries, sources = raw
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        assert e["kind"] in KINDS and e["id"].startswith(f"{e['kind']}.")
        assert e["group"] in reference.GROUPS or e["group"].removeprefix("stage:") in reference.STAGES
        pt, en = e["text"]["pt"], e["text"]["en"]
        assert set(pt) == set(en), f"{e['id']}: sections differ between languages"
        assert pt.get("summary") and set(pt) <= set(SECTIONS)
        assert all(text.strip() and "—" not in text for text in (*pt.values(), *en.values()))
        assert not [r for r in e["related"] if r not in ids], f"{e['id']}: unknown related entry"
        assert not [s for s in e["sources"] if s not in sources], f"{e['id']}: unknown source"
    for key, source in SOURCES.items():
        assert source["url"].startswith("https://") and source["title"], key
    cited = {s for e in entries for s in e["sources"]}
    assert not set(SOURCES) - cited, "sources nobody cites"


def test_catalog_is_localized_and_filterable():
    pt, en = reference.catalog("pt"), reference.catalog("en")
    assert [e["id"] for e in pt["entries"]] == [e["id"] for e in en["entries"]]
    recall_pt = next(e for e in pt["entries"] if e["id"] == "metric.recall")
    recall_en = next(e for e in en["entries"] if e["id"] == "metric.recall")
    assert recall_pt["summary"] != recall_en["summary"]
    assert [s["key"] for s in recall_pt["sections"]] == ["how", "read", "limits"]
    assert all(e["group"] in pt["groups"] for e in pt["entries"])
    only = reference.catalog("pt", "metric")
    assert {e["kind"] for e in only["entries"]} == {"metric"}
    assert set(only["sources"]) == {s for e in only["entries"] for s in e["sources"]}
    assert reference.show("technique.hyde")["sources"][0]["url"].startswith("https://aclanthology.org")
