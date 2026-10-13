import pytest

from ragstudio.core import registry
from ragstudio.core.contract import Param, TechniqueRequest, TechniqueResult, TechniqueSpec, validate_result
from ragstudio.core.errors import NotFoundError, ValidationError
from ragstudio.core.hashing import canonical_json, sha256_json
from ragstudio.core.models import Answer, Chunk, Context, Query, RetrievedChunk, StageTiming, Usage
from ragstudio.core.pipeline import format_context, merge_pool
from ragstudio.prompts import PromptSet


def chunk(i, text="texto", doc="d"):
    return Chunk(id=f"{doc}:{i}", document_id=doc, index=i, text=text, char_start=i * 10, char_end=i * 10 + 5)


def result(spec_name="x", stages=("retrieval", "generation"), citations=None, diagnostics=None):
    items = (RetrievedChunk(chunk(0), 0.9, 1, "dense"),)
    return TechniqueResult(
        answer=Answer("a"), contexts=items, context=Context("ctx", ("d:0",), 3, False),
        citations=tuple(citations if citations is not None else [{"chunk_id": "d:0"}]),
        diagnostics=diagnostics if diagnostics is not None else {"technique": spec_name},
        timings=tuple(StageTiming(s, 0.1) for s in stages), usage=Usage())


SPEC = TechniqueSpec(name="x", version="1", family="t", description="d",
                     params={"n": Param(3), "mode": Param("a", choices=("a", "b")), "ratio": Param(0.5)})


def test_models_roundtrip():
    c = chunk(2, "abc")
    assert Chunk.from_dict(c.to_dict()) == c
    item = RetrievedChunk(c, 0.5, 1, "dense")
    assert item.with_text("novo", compressed=True).chunk.metadata == {"compressed": True}
    assert item.with_rank(3, score=0.1).rank == 3 and item.to_dict()["chunk"]["id"] == "d:2"
    assert Query("q", "?").to_dict()["answer_type"] == "extraction"


def test_canonical_hash_ignores_key_order():
    assert sha256_json({"b": 1, "a": [1, 2]}) == sha256_json({"a": [1, 2], "b": 1})
    assert canonical_json({"b": 1, "a": "é"}) == '{"a":"é","b":1}'


def test_spec_resolves_defaults_and_coerces():
    assert SPEC.resolve({"n": "5", "ratio": 1}) == {"n": 5, "mode": "a", "ratio": 1.0}
    with pytest.raises(ValidationError, match="unknown parameter"):
        SPEC.resolve({"nope": 1})
    with pytest.raises(ValidationError, match="not in"):
        SPEC.resolve({"mode": "z"})


def test_spec_rejects_unknown_status():
    with pytest.raises(ValidationError):
        TechniqueSpec(name="y", version="1", family="t", description="d", status="done")


def test_validate_result_accepts_valid():
    assert validate_result(result(), SPEC).answer.text == "a"


@pytest.mark.parametrize("bad, message", [
    (lambda: {"answer": "text"}, "must return TechniqueResult"),
    (lambda: result(stages=("retrieval",)), "timings must cover"),
    (lambda: result(citations=[{"chunk_id": "other"}]), "is not in contexts"),
    (lambda: result(diagnostics={"technique": "wrong"}), "diagnostics"),
    (lambda: result(diagnostics={"technique": "x", "obj": object()}), "not JSON serializable"),
])
def test_validate_result_rejects_invalid(bad, message):
    with pytest.raises(ValidationError, match=message):
        validate_result(bad(), SPEC)


def test_registry_discovers_builtin_and_requires_known_name():
    names = set(registry.reload())
    assert {"naive", "hyde", "multi_query", "decomposition", "iterative", "context_compression", "mmr_rag",
            "rag_evo"} <= names
    with pytest.raises(NotFoundError, match="unknown technique"):
        registry.get("does-not-exist")


def test_registry_discovers_external_technique_without_touching_core(tmp_path, monkeypatch, make_deps):
    (tmp_path / "shout.py").write_text('''
from ragstudio.core.contract import TechniqueSpec
from ragstudio.core.pipeline import finish, generate

SPEC = TechniqueSpec(name="shout", version="0.1", family="demo", description="naive, upper-cased")


def run(request, deps):
    with deps.stage("retrieval"):
        chunks = deps.retrieve(request.query.text, request.k)
    answer, context = generate(deps, request.query.text, chunks, request.max_context_chars)
    return finish(SPEC, deps, type(answer)(answer.text.upper()), chunks, context)
''', encoding="utf-8")
    (tmp_path / "_helper.py").write_text("X = 1\n", encoding="utf-8")
    monkeypatch.setenv("RAGSTUDIO_TECHNIQUES_PATH", str(tmp_path))
    try:
        technique = registry.reload()["shout"]
        deps, _ = make_deps()
        out = validate_result(technique.run(TechniqueRequest(Query("q", "Qual é o limite de Betz?"), k=2), deps),
                              technique.spec)
        assert out.answer.text.isupper()
    finally:
        monkeypatch.delenv("RAGSTUDIO_TECHNIQUES_PATH")
        registry.reload()


def test_registry_rejects_module_without_run(tmp_path, monkeypatch):
    (tmp_path / "broken.py").write_text(
        'from ragstudio.core.contract import TechniqueSpec\n'
        'SPEC = TechniqueSpec(name="broken", version="1", family="t", description="d")\n', encoding="utf-8")
    monkeypatch.setenv("RAGSTUDIO_TECHNIQUES_PATH", str(tmp_path))
    try:
        with pytest.raises(ValidationError, match="must define SPEC"):
            registry.reload()
    finally:
        monkeypatch.delenv("RAGSTUDIO_TECHNIQUES_PATH")
        registry.reload()


def test_format_context_truncates_and_reports():
    items = [RetrievedChunk(chunk(i, "x" * 400), 1.0 - i / 10, i + 1, "dense") for i in range(4)]
    full = format_context(items, 10_000)
    assert full.truncated is False and len(full.chunk_ids) == 4 and full.text.startswith("[1] (d · chunk 0)")
    cut = format_context(items, 900)
    assert cut.truncated is True and len(cut.chunk_ids) < 4 and cut.chars <= 900


def test_merge_pool_keeps_best_score_and_reranks():
    a = [RetrievedChunk(chunk(0), 0.2, 1, "dense"), RetrievedChunk(chunk(1), 0.9, 2, "dense")]
    b = [RetrievedChunk(chunk(0), 0.7, 1, "bm25")]
    pool = merge_pool(a, b)
    assert [(p.chunk.id, p.score, p.rank) for p in pool] == [("d:1", 0.9, 1), ("d:0", 0.7, 2)]


def test_prompts_render_and_hash_are_stable():
    prompts = PromptSet("pt")
    rendered = prompts.render("rerank", query="q", passages=["a", "b"])
    assert "[1] a\n[2] b" in rendered.user and rendered.template_sha256 == prompts.template_hash("rerank")
    assert PromptSet("en").template_hash("answer") != prompts.template_hash("answer")
    with pytest.raises(ValidationError, match="missing variable"):
        prompts.render("answer", query="q")
    with pytest.raises(ValidationError, match="no prompt templates"):
        PromptSet("xx")
