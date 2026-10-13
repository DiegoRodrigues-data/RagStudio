import numpy as np
import pytest

from ragstudio.core.errors import NotFoundError, ValidationError
from ragstudio.core.models import Chunk, RetrievedChunk
from ragstudio.experiments.index_builder import build_index, compute_index_hash, load_index
from ragstudio.providers import routing
from ragstudio.rerankers import build as build_reranker
from ragstudio.rerankers.llm import parse_order
from ragstudio.retrieval import retrieve
from ragstudio.retrieval.fusion import rrf
from ragstudio.retrieval.mmr import mmr_select
from ragstudio.stores import MemoryStore, load

QUESTION = "Qual é o limite de Betz para o aproveitamento da energia do vento?"


def embed_query(text):
    return routing.embed(routing.resolve_endpoint("embedding"), [text]).vectors[0]


def test_index_is_reused_by_hash(documents, store):
    emb = routing.resolve_endpoint("embedding")
    again, reused = build_index(documents, corpus_id="c", chunking={"size": 300, "overlap": 50}, embedder=emb)
    assert reused and again.meta.index_hash == store.meta.index_hash
    other = compute_index_hash(documents, {"size": 301, "overlap": 50}, emb)
    assert other != store.meta.index_hash
    assert compute_index_hash(documents[:2], {"size": 300, "overlap": 50}, emb) != store.meta.index_hash
    assert store.meta.chunking_profile["chunks"] == store.meta.chunks > 0 and store.meta.dim == 96


def test_persist_and_load_roundtrip(store):
    loaded = load(store.path)
    assert isinstance(loaded, MemoryStore) and loaded.meta.to_dict() == store.meta.to_dict()
    assert [c.id for c in loaded.all_chunks()] == [c.id for c in store.all_chunks()]
    vector = embed_query(QUESTION)
    assert [c.id for c, _ in loaded.dense_search(vector, 5)] == [c.id for c, _ in store.dense_search(vector, 5)]
    assert loaded.document_text("energia-solar").startswith("# Energia solar")
    assert load_index(store.meta.index_hash[:10]).meta.index_hash == store.meta.index_hash
    with pytest.raises(NotFoundError):
        load_index("ffffffff")


def test_dense_and_bm25_find_the_gold_chunk(store):
    dense = retrieve(store, embed_query, QUESTION, 3, mode="dense")
    lexical = retrieve(store, embed_query, QUESTION, 3, mode="bm25")
    assert dense[0].chunk.document_id == "energia-eolica" and "Betz" in dense[0].chunk.text
    assert "Betz" in lexical[0].chunk.text and [h.rank for h in lexical] == [1, 2, 3]
    assert [h.source for h in dense] == ["dense"] * 3 and dense[0].score >= dense[1].score >= dense[2].score


@pytest.mark.parametrize("mode", ["dense", "bm25", "hybrid", "rrf", "mmr"])
def test_every_mode_returns_ranked_unique_chunks(store, mode):
    hits = retrieve(store, embed_query, QUESTION, 4, mode=mode)
    assert 0 < len(hits) <= 4 and len({h.chunk.id for h in hits}) == len(hits)
    assert [h.rank for h in hits] == list(range(1, len(hits) + 1)) and hits[0].source == mode


def test_filters_restrict_documents(store):
    hits = retrieve(store, embed_query, QUESTION, 5, mode="hybrid", filters={"document_id": "hidreletricas"})
    assert hits and {h.chunk.document_id for h in hits} == {"hidreletricas"}
    assert retrieve(store, embed_query, QUESTION, 5, mode="dense", filters={"document_id": "nope"}) == []


def test_dimension_mismatch_is_explicit(store):
    with pytest.raises(ValidationError, match="embedding dimension mismatch"):
        store.dense_search([0.1] * 8, 3)
    with pytest.raises(ValidationError, match="unknown retrieval mode"):
        retrieve(store, embed_query, QUESTION, 3, mode="magic")


def test_query_vector_overrides_query_embedding(store):
    other = embed_query("usina de Itaipu unidades geradoras")
    hits = retrieve(store, embed_query, QUESTION, 1, mode="dense", query_vector=other)
    assert hits[0].chunk.id == store.dense_search(other, 1)[0][0].id
    assert hits[0].chunk.id != retrieve(store, embed_query, QUESTION, 1, mode="dense")[0].chunk.id


def _item(i, score):
    return RetrievedChunk(Chunk(f"d:{i}", "d", i, "t", 0, 1), score, 0, "x")


def test_rrf_rewards_agreement():
    fused = rrf([[_item(1, 9), _item(2, 8), _item(3, 7)], [_item(3, 5), _item(2, 4), _item(4, 3)]], k=4, rrf_k=60)
    # d:3 is ranked 3rd and 1st, d:2 twice 2nd, d:1 and d:4 appear in one list only
    assert [f.chunk.id for f in fused] == ["d:3", "d:2", "d:1", "d:4"] and fused[0].source == "rrf"
    assert fused[0].score == pytest.approx(1 / 63 + 1 / 61, abs=1e-6)
    assert fused[1].score == pytest.approx(2 / 62, abs=1e-6)


def test_mmr_lambda_extremes():
    query = [1.0, 0.0]
    docs = [[1.0, 0.0], [0.99, 0.14], [0.6, 0.8], [0.0, 1.0]]
    assert mmr_select(query, docs, 3, lambda_=1.0) == [0, 1, 2]          # pure relevance
    assert mmr_select(query, docs, 2, lambda_=0.0) == [0, 3]             # most dissimilar after the first pick
    assert mmr_select(query, [], 3) == []
    assert np.isfinite(mmr_select(query, docs, 4, lambda_=0.5)).all()


def test_rerankers(make_deps, store):
    pool = retrieve(store, embed_query, QUESTION, 8, mode="dense")
    lexical = build_reranker("lexical")(QUESTION, list(reversed(pool)), 3)
    assert len(lexical) == 3 and "Betz" in lexical[0].chunk.text and lexical[0].source == "rerank:lexical"
    deps, rec = make_deps(reranker="llm")
    llm = deps.rerank(QUESTION, list(reversed(pool)), 3)
    assert "Betz" in llm[0].chunk.text and rec.calls_by_task == {"rerank": 1} and deps.has_reranker
    assert build_reranker("none") is None
    with pytest.raises(ValidationError):
        build_reranker("magic")


def test_llm_rerank_order_parsing_is_defensive():
    assert parse_order("3, 1", 4) == [2, 0, 1, 3]
    assert parse_order("9, 2, 2, zero", 3) == [1, 0, 2]
    assert parse_order("no numbers here", 3) == [0, 1, 2]


def test_cross_encoder_reports_missing_dependency():
    try:
        import sentence_transformers  # noqa: F401
        pytest.skip("sentence-transformers installed")
    except ImportError:
        pass
    with pytest.raises(ValidationError, match="sentence-transformers"):
        build_reranker("cross_encoder")


def test_duckdb_store_matches_memory_store(documents, store):
    pytest.importorskip("duckdb")
    emb = routing.resolve_endpoint("embedding")
    duck, reused = build_index(documents, corpus_id="c", chunking={"size": 300, "overlap": 50}, embedder=emb,
                               store="duckdb")
    assert not reused and duck.meta.store == "duckdb" and duck.meta.index_hash != store.meta.index_hash
    vector = embed_query(QUESTION)
    assert [c.id for c, _ in duck.dense_search(vector, 5)] == [c.id for c, _ in store.dense_search(vector, 5)]
    lexical = duck.lexical_search(QUESTION, 3)
    assert lexical and "Betz" in lexical[0][0].text and duck.lexical_backend in ("duckdb-fts", "memory-bm25")
    reloaded = load(duck.path)
    assert type(reloaded).__name__ == "DuckDBStore"
    assert [c.id for c, _ in reloaded.dense_search(vector, 3)] == [c.id for c, _ in store.dense_search(vector, 3)]
    assert {c.document_id for c, _ in reloaded.dense_search(vector, 5, {"document_id": "energia-solar"})} == {
        "energia-solar"}


def test_contextual_enrichment_changes_index_text_not_chunk_text(documents):
    emb, llm = routing.resolve_endpoint("embedding"), routing.resolve_endpoint("llm")
    built, _ = build_index(documents, corpus_id="c", chunking={"size": 300, "overlap": 50}, embedder=emb,
                           enrich="contextual", llm=llm)
    chunk = built.all_chunks()[3]
    doc = next(d for d in documents if d.id == chunk.document_id)
    assert chunk.metadata["context_prefix"] and doc.text[chunk.char_start:chunk.char_end] == chunk.text
    assert built.meta.enrich == "contextual" and built.meta.build_usage["llm_calls"] == built.meta.chunks
    with pytest.raises(ValidationError, match="needs an LLM"):
        build_index(documents, corpus_id="c", chunking=None, embedder=emb, enrich="contextual")


@pytest.mark.parametrize(("kind", "module", "cls"), [("faiss", "faiss", "FaissStore"),
                                                     ("chroma", "chromadb", "ChromaStore")])
def test_vector_db_stores_match_memory_store(documents, store, kind, module, cls):
    pytest.importorskip(module)
    emb = routing.resolve_endpoint("embedding")
    chunking = {"size": 300, "overlap": 50}
    built, reused = build_index(documents, corpus_id="c", chunking=chunking, embedder=emb, store=kind)
    assert not reused and built.meta.store == kind and built.meta.index_hash != store.meta.index_hash
    assert type(built).__name__ == cls
    vector = embed_query(QUESTION)
    expected = store.dense_search(vector, 5)
    for candidate in (built, load(built.path)):
        assert type(candidate).__name__ == cls
        hits = candidate.dense_search(vector, 5)
        assert [c.id for c, _ in hits] == [c.id for c, _ in expected]
        assert [s for _, s in hits] == pytest.approx([s for _, s in expected], abs=1e-4)
        assert "Betz" in candidate.lexical_search(QUESTION, 3)[0][0].text
        assert candidate.dense_search(vector, 0) == []
        doc_id = expected[-1][0].document_id
        filtered = candidate.dense_search(vector, 50, {"document_id": doc_id})
        assert [c.id for c, _ in filtered] == [c.id for c, _ in store.dense_search(vector, 50,
                                                                                    {"document_id": doc_id})]
        with pytest.raises(ValidationError, match="dimension mismatch"):
            candidate.dense_search([0.1, 0.2], 3)
        assert [h.chunk.id for h in retrieve(candidate, embed_query, QUESTION, 4, mode="rrf")] == \
               [h.chunk.id for h in retrieve(store, embed_query, QUESTION, 4, mode="rrf")]
    again, reused = build_index(documents, corpus_id="c", chunking=chunking, embedder=emb, store=kind)
    assert reused and type(again).__name__ == cls
    forced, reused = build_index(documents, corpus_id="c", chunking=chunking, embedder=emb, store=kind, force=True)
    assert not reused
    assert [c.id for c, _ in forced.dense_search(vector, 5)] == [c.id for c, _ in expected]


@pytest.mark.parametrize(("kind", "module", "package"), [("faiss", "faiss", "faiss-cpu"),
                                                         ("chroma", "chromadb", "chromadb")])
def test_vector_db_stores_report_missing_dependency(monkeypatch, kind, module, package):
    import sys

    from ragstudio.stores import IndexMeta, create
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.setitem(sys.modules, module, None)
    with pytest.raises(ValidationError, match=f"pip install {package}"):
        create(kind, IndexMeta(index_hash="h", corpus_id="c", chunking={}, embedding_model="m"))


def test_faiss_refuses_to_load_next_to_torch(monkeypatch):
    import sys

    from ragstudio.stores.faiss import _faiss
    monkeypatch.delitem(sys.modules, "faiss", raising=False)
    monkeypatch.setitem(sys.modules, "torch", object())
    with pytest.raises(ValidationError, match="PyTorch"):
        _faiss()
