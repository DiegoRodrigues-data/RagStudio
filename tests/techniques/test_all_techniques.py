"""Every registered technique goes through the same request, the same deps and the same validation."""
import json

import pytest

from ragstudio.core import registry
from ragstudio.core.contract import IGNORABLE, PIPELINE_STAGES, TechniqueRequest, validate_result
from ragstudio.core.errors import ValidationError
from ragstudio.core.models import Query

NAMES = sorted(registry.all_techniques())
QUESTION = Query("q1", "Qual é o limite de Betz para o aproveitamento da energia do vento?")
EXPECTED = {"light_rag", "hippo_rag", "hybrid_rag", "rag_fusion", "multi_hop", "adaptive_rag", "self_rag",
            "rank_rag", "long_context", "hierarchical", "recomp", "speculative_rag", "naive", "hyde", "multi_query", "decomposition", "iterative", "context_compression", "mmr_rag", "rag_evo",
            "step_back", "parent_child", "sentence_window", "contextual_retrieval", "corrective", "raptor",
            "graph_rag", "agentic"}


def test_catalog_is_complete_and_honest():
    assert set(NAMES) == EXPECTED
    statuses = {name: registry.get(name).spec.status for name in NAMES}
    assert {n for n, s in statuses.items() if s == "prototype"} == {"self_rag", "rank_rag", "recomp", "speculative_rag"}
    for name in NAMES:
        spec = registry.get(name).spec
        assert spec.version and spec.family and spec.description and spec.reference.startswith("http")
        assert spec.title and spec.stage in PIPELINE_STAGES and set(spec.ignored_axes()) <= set(IGNORABLE)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("variant", ["plain", "llm-rerank", "hybrid"])
def test_contract(name, variant, make_deps):
    overrides = {"plain": {}, "llm-rerank": {"reranker": "llm"}, "hybrid": {"retrieval_mode": "hybrid"}}[variant]
    technique = registry.get(name)
    deps, recorder = make_deps(**overrides)
    result = validate_result(technique.run(TechniqueRequest(QUESTION, k=3, max_context_chars=4000), deps),
                             technique.spec)
    assert result.answer.text and 0 < len(result.contexts) <= 4, "k chunks, plus at most one synthetic passage"
    assert "Betz" in result.context.text, "the gold passage should reach the context with the mock provider"
    assert result.usage.llm_calls >= 1 and result.usage.calls_by_task.get("answer", 0) >= 1
    assert result.usage.llm_calls == sum(1 for e in recorder.events if e["kind"] == "request")
    assert sum(1 for e in recorder.events if e["kind"] == "retrieval") >= 1
    assert all(t.seconds >= 0 for t in result.timings)
    assert [c.rank for c in result.contexts] == list(range(1, len(result.contexts) + 1))
    json.dumps(result.to_dict(), ensure_ascii=False)


@pytest.mark.parametrize("name", NAMES)
def test_deterministic_with_mock(name, make_deps):
    technique = registry.get(name)
    runs = []
    for _ in range(2):
        deps, _ = make_deps()
        out = technique.run(TechniqueRequest(QUESTION, k=3), deps)
        runs.append((out.answer.text, [c.chunk.id for c in out.contexts]))
    assert runs[0] == runs[1]


@pytest.mark.parametrize("name", NAMES)
def test_unknown_parameter_is_rejected(name, make_deps):
    deps, _ = make_deps()
    with pytest.raises(ValidationError, match="unknown parameter"):
        registry.get(name).run(TechniqueRequest(QUESTION, k=3, params={"no_such_param": 1}), deps)


@pytest.mark.parametrize("name", NAMES)
def test_small_context_budget_is_respected(name, make_deps):
    if "max_context_chars" in registry.get(name).spec.ignored_axes():
        pytest.skip("this technique declares its own context budget")
    deps, _ = make_deps()
    result = registry.get(name).run(TechniqueRequest(QUESTION, k=3, max_context_chars=350), deps)
    assert result.context.chars <= 350 and set(result.context.chunk_ids) <= {c.chunk.id for c in result.contexts}
