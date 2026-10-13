"""Behaviour that is specific to each technique (what makes it that technique)."""
import importlib.util

import numpy as np
import pytest

from ragstudio.core import registry
from ragstudio.core.contract import TechniqueRequest, validate_result
from ragstudio.core.errors import ProviderError, ValidationError
from ragstudio.core.models import Query
from ragstudio.experiments.index_builder import build_index
from ragstudio.providers import mock, routing
from ragstudio.stores.graph import KnowledgeGraph, louvain
from ragstudio.techniques import hippo_rag, light_rag, rank_rag, self_rag, speculative_rag
from ragstudio.techniques.agentic import technique as agentic
from ragstudio.techniques.rag_evo import confidence, heuristics
from ragstudio.techniques.raptor import technique as raptor

Q = Query("q1", "Qual é o limite de Betz para o aproveitamento da energia do vento?")
MULTI = Query("q2", "Qual é o limite de Betz e onde foi instalado o primeiro aerogerador do Brasil?")


def run(name, deps, query=Q, k=3, **params):
    return registry.get(name).run(TechniqueRequest(query, k=k, params=params), deps)


def test_naive_retrieval_mode_override(make_deps):
    deps, rec = make_deps()
    out = run("naive", deps, retrieval_mode="bm25")
    assert out.diagnostics["retrieval_mode"] == "bm25" and {c.source for c in out.contexts} == {"bm25"}
    assert out.usage.embedding_calls == 0 and out.usage.llm_calls == 1


def test_hyde_retrieves_with_hypothetical_document(make_deps):
    deps, rec = make_deps()
    out = run("hyde", deps)
    retrieval = next(e["payload"] for e in rec.events if e["kind"] == "retrieval")
    assert retrieval["query"] == out.diagnostics["hypothetical_document"] != Q.text
    assert out.usage.calls_by_task == {"hypo_doc": 1, "answer": 1}
    assert [t.stage for t in out.timings][:2] == ["query_transform", "retrieval"]


def test_multi_query_pools_and_reports_contributions(make_deps):
    deps, rec = make_deps()
    out = run("multi_query", deps, n_queries=3)
    assert len(out.diagnostics["queries"]) == 3 and out.diagnostics["queries"][0] == Q.text
    assert sum(1 for e in rec.events if e["kind"] == "retrieval") == 3
    assert len(out.diagnostics["contributions"]) == 3
    deps, _ = make_deps()
    assert run("multi_query", deps, fusion="rrf").diagnostics["fusion"] == "rrf"
    deps, rec = make_deps()
    assert run("multi_query", deps, n_queries=1).usage.calls_by_task == {"answer": 1}


def test_decomposition_covers_both_parts_of_a_compound_question(make_deps):
    deps, rec = make_deps(retrieval_mode="bm25")  # lexical: the hashed mock embedding is too coarse for this check
    out = run("decomposition", deps, query=MULTI, k=4)
    assert len(out.diagnostics["subquestions"]) == 2
    assert sum(1 for e in rec.events if e["kind"] == "retrieval") == 3  # original + two sub-questions
    assert "Betz" in out.context.text and "Fernando de Noronha" in out.context.text


def test_iterative_runs_the_requested_rounds(make_deps):
    deps, _ = make_deps()
    out = run("iterative", deps, rounds=3)
    assert [t["round"] for t in out.diagnostics["trace"]] == [1, 2, 3]
    assert out.usage.calls_by_task == {"answer": 3, "gap_query": 2}
    assert out.diagnostics["trace"][1]["query"] != Q.text


def test_context_compression_shrinks_context(make_deps):
    deps, _ = make_deps()
    out = run("context_compression", deps)
    assert 0 < out.diagnostics["compression_ratio"] < 1
    assert out.diagnostics["chars_after"] < out.diagnostics["chars_before"]
    assert all(c.chunk.metadata.get("compressed") for c in out.contexts)
    assert "compression" in [t.stage for t in out.timings]


def test_mmr_diversity_changes_selection(make_deps):
    deps, _ = make_deps()
    relevant = run("mmr_rag", deps, k=4, lambda_=1.0)
    deps, _ = make_deps()
    diverse = run("mmr_rag", deps, k=4, lambda_=0.1)
    assert {c.source for c in diverse.contexts} == {"mmr"}
    assert [c.chunk.id for c in relevant.contexts] != [c.chunk.id for c in diverse.contexts]
    assert diverse.diagnostics["documents_in_context"] >= relevant.diagnostics["documents_in_context"]


def test_rag_evo_heuristics_port():
    assert heuristics.score_len("", 800) == 0.0 and heuristics.score_len("x" * 400, 800) == 0.5
    assert heuristics.score_entropy("vento vento vento") == 0.0
    assert heuristics.score_entropy("turbina eólica extrai energia cinética") == pytest.approx(1.0)
    assert heuristics.score_coverage("limite betz turbina", ["o limite de Betz vale para toda turbina"]) == 3 / 8
    score = heuristics.confidence_score("limite betz turbina", ["o limite de Betz vale para toda turbina"])
    assert score["confidence"] == pytest.approx(0.34 * score["len"] + 0.33 * score["entropy"] + 0.33 * score["coverage"],
                                                abs=1e-5)
    assert confidence.heuristic_confidence("") == 0.0 and confidence.heuristic_confidence("x" * 300) == 0.75
    assert confidence.llm_confidence(lambda task, **v: "0,8", "q", "a", "c") == (0.8, True)
    assert confidence.llm_confidence(lambda task, **v: "no idea", "q", "a", "c") == (0.5, False)


def test_rag_evo_stops_on_threshold_or_recovers(make_deps):
    deps, _ = make_deps()
    easy = run("rag_evo", deps, confidence_threshold=0.1, rounds=3)
    assert easy.diagnostics["rounds_run"] == 1 and not easy.diagnostics["needs_review"]
    deps, _ = make_deps()
    hard = run("rag_evo", deps, confidence_threshold=0.99, rounds=3)
    assert hard.diagnostics["rounds_run"] == 3 and hard.diagnostics["needs_review"]
    assert hard.usage.calls_by_task == {"answer": 3, "gap_query": 2}
    assert hard.diagnostics["best_confidence"] == max(t["confidence"] for t in hard.diagnostics["traces"])
    deps, _ = make_deps()
    llm_mode = run("rag_evo", deps, confidence_mode="llm", rounds=1)
    assert llm_mode.usage.calls_by_task["confidence"] == 1 and llm_mode.diagnostics["traces"][0]["mode"] == "llm"
    deps, _ = make_deps()
    assert {c.source for c in run("rag_evo", deps, use_mmr=False).contexts} == {"dense"}


def test_step_back_adds_a_general_query(make_deps):
    deps, rec = make_deps()
    out = run("step_back", deps)
    queries = [e["payload"]["query"] for e in rec.events if e["kind"] == "retrieval"]
    assert queries == [Q.text, out.diagnostics["step_back_question"]]


def test_parent_child_expands_to_parent_span(documents, make_deps):
    index, _ = build_index(documents, corpus_id="c", embedder=routing.resolve_endpoint("embedding"),
                           chunking={"strategy": "parent_child", "size": 150, "overlap": 20, "parent_size": 600})
    deps, _ = make_deps(index)
    out = run("parent_child", deps, k=2)
    assert not out.warnings and out.diagnostics["orphans"] == 0
    for item in out.contexts:
        text = index.document_text(item.chunk.document_id)
        assert text[item.chunk.char_start:item.chunk.char_end].strip() == item.chunk.text
        assert len(item.chunk.text) > 150 and item.source.endswith("+parent")
    deps, _ = make_deps()
    assert "no parent span" in run("parent_child", deps).warnings[0]


def test_sentence_window_expands_and_stays_anchored(make_deps, store):
    deps, _ = make_deps()
    out = run("sentence_window", deps, window=1)
    assert out.diagnostics["chars_expanded"] > out.diagnostics["chars_matched"]
    for item in out.contexts:
        text = store.document_text(item.chunk.document_id)
        assert text[item.chunk.char_start:item.chunk.char_end].strip() == item.chunk.text
    spans = sorted((c.chunk.document_id, c.chunk.char_start, c.chunk.char_end) for c in out.contexts)
    assert all(a[0] != b[0] or a[2] < b[1] for a, b in zip(spans, spans[1:], strict=False)), "windows must not overlap"


def test_contextual_retrieval_uses_enriched_index(documents, make_deps):
    emb, llm = routing.resolve_endpoint("embedding"), routing.resolve_endpoint("llm")
    index, _ = build_index(documents, corpus_id="c", chunking={"size": 300, "overlap": 50}, embedder=emb,
                           enrich="contextual", llm=llm)
    deps, _ = make_deps(index)
    out = run("contextual_retrieval", deps)
    assert out.diagnostics["index_enriched"] and not out.warnings and out.diagnostics["with_prefix"] == 3
    deps, _ = make_deps()
    assert "equivalent to naive" in run("contextual_retrieval", deps).warnings[0]


def test_corrective_grades_and_filters(make_deps):
    deps, _ = make_deps()
    out = run("corrective", deps)
    decisions = out.diagnostics["decisions"]
    assert out.diagnostics["graded"] == 6 and 0 < out.diagnostics["relevant"] < 6
    kept = {d["chunk_id"] for d in decisions if d["relevant"]}
    assert {c.chunk.id for c in out.contexts} <= kept and out.diagnostics["action"] == "correct"
    deps, _ = make_deps()
    off_topic = run("corrective", deps, query=Query("q", "Qual a capital da Mongólia e a sua população?"))
    assert off_topic.diagnostics["action"] == "incorrect" and off_topic.diagnostics["rewritten_query"]


def test_raptor_builds_a_recursive_tree_once(make_deps, store):
    deps, _ = make_deps()
    first = run("raptor", deps, summary_input_chars=900)
    deps, _ = make_deps()
    second = run("raptor", deps, summary_input_chars=900)
    assert first.diagnostics["built_now"] and not second.diagnostics["built_now"]
    assert first.diagnostics["levels"] >= 2 and first.diagnostics["reduction"] in ("pca", "umap")
    assert first.diagnostics["summaries"] == sum(first.diagnostics["summaries_per_level"].values()) >= 2
    assert first.usage.calls_by_task["summarize"] == first.diagnostics["summaries"]
    assert "summarize" not in second.usage.calls_by_task
    assert any(p.name.startswith("aux_raptor_") for p in store.path.iterdir())
    deps, rec = make_deps()
    walked = run("raptor", deps, summary_input_chars=900, mode="tree_traversal")
    assert not walked.diagnostics["built_now"], "both query modes share the same tree"
    assert {c.source for c in walked.contexts} <= {"raptor:leaf", "raptor:summary"} and "Betz" in walked.context.text
    assert any(e["payload"]["mode"] == "raptor:tree_traversal" for e in rec.events if e["kind"] == "retrieval")


def test_raptor_soft_clustering_and_missing_umap(make_deps):
    data = np.vstack([np.random.default_rng(0).normal(center, 0.3, (30, 4)) for center in (0.0, 3.0, 6.0)])
    clusters = raptor.soft_clusters(data, 50, 0.1, 42)
    assert sorted(len(c) for c in clusters) == [30, 30, 30]
    assert len(raptor.soft_clusters(data, 50, 1e-9, 42)) == 3 and sum(map(len, raptor.soft_clusters(data, 50, 0.0, 42))) > 90
    if importlib.util.find_spec("umap") is None:
        deps, _ = make_deps()
        with pytest.raises(ValidationError, match="pip install umap-learn"):
            run("raptor", deps, reduction="umap")


def test_knowledge_graph_parsing_and_communities():
    graph = KnowledgeGraph()
    graph.add_extraction("c1", "ENTITY | Albert Betz | pessoa | físico alemão\n- REL | Albert Betz | Limite de Betz "
                               "| formulou | demonstrado em 1919\nlinha solta\nENTITY | X", 12)
    graph.add_extraction("c2", "REL | Limite de Betz | Turbina | limita | aproveitamento máximo de 59,3%", 12)
    assert set(graph.entities) == {"albert betz", "limite de betz", "turbina"}
    assert graph.entities["albert betz"]["type"] == "pessoa" and graph.entities["limite de betz"]["chunks"] == ["c1", "c2"]
    assert "formulou" in graph.relation_text(next(iter(graph.relations.values())))
    assert graph.match("O que diz o limite de Betz?") == ["limite de betz"]
    adjacency: dict[str, dict[str, float]] = {"alone": {}}
    for a, b in [("a", "b"), ("b", "c"), ("a", "c"), ("d", "e"), ("e", "f"), ("d", "f"), ("c", "d")]:
        adjacency.setdefault(a, {})[b] = adjacency.setdefault(b, {})[a] = 1.0
    finest = louvain(adjacency)[0]
    assert finest["a"] == finest["b"] == finest["c"] != finest["d"] == finest["e"] == finest["f"]
    assert finest["alone"] == "alone"


def test_graph_rag_local_and_global_search(make_deps):
    deps, rec = make_deps()
    out = run("graph_rag", deps, k=4)
    diag = out.diagnostics
    assert diag["built_now"] and diag["graph_entities"] > 5 and diag["graph_relations"] > 0 and diag["communities"] >= 1
    assert any("Betz" in e for e in diag["question_entities"]) and diag["graph_candidates"] >= 1
    assert out.usage.calls_by_task["community_report"] == diag["communities"]
    assert out.contexts[-1].source == "graphrag:community" and out.contexts[-1].chunk.id == diag["community_report"]
    assert {e["payload"]["mode"] for e in rec.events if e["kind"] == "retrieval"} == {"graphrag:local", "dense"}
    deps, _ = make_deps()
    pure = run("graph_rag", deps, dense_fusion=False, include_report=False)
    assert not pure.diagnostics["built_now"] and {c.source for c in pure.contexts} == {"graphrag:local"}
    deps, _ = make_deps()
    wide = run("graph_rag", deps, mode="global")
    assert wide.diagnostics["mode"] == "global" and {c.source for c in wide.contexts} == {"graphrag:community"}
    assert wide.usage.calls_by_task["community_points"] == wide.diagnostics["reports_mapped"]
    assert "kg_extract" not in wide.usage.calls_by_task and "Betz" in wide.context.text


def test_graph_techniques_share_one_extraction(make_deps, store):
    deps, _ = make_deps()
    first = run("light_rag", deps, k=4)
    assert first.diagnostics["built_now"] and first.usage.calls_by_task["kg_extract"] == len(store.all_chunks())
    for name in ("graph_rag", "hippo_rag", "light_rag"):
        deps, _ = make_deps()
        assert "kg_extract" not in run(name, deps).usage.calls_by_task, name


def test_light_rag_levels(make_deps):
    deps, rec = make_deps()
    mix = run("light_rag", deps, k=4)
    assert mix.diagnostics["low_level_keywords"] and mix.diagnostics["high_level_keywords"]
    assert mix.contexts[-1].source == "lightrag:graph" and "Entidades:" in mix.contexts[-1].chunk.text
    modes = [e["payload"]["mode"] for e in rec.events if e["kind"] == "retrieval"]
    assert modes == ["lightrag:local", "lightrag:global", "dense"]
    deps, rec = make_deps()
    local = run("light_rag", deps, mode="local", k=2)
    assert {c.source for c in local.contexts} == {"lightrag:local"}, "with k < 3 there is no room for the graph passage"
    assert [e["payload"]["mode"] for e in rec.events if e["kind"] == "retrieval"] == ["lightrag:local"]
    deps, _ = make_deps()
    assert {c.source for c in run("light_rag", deps, mode="global", k=2).contexts} == {"lightrag:global"}
    assert light_rag.parse_keywords("- HIGH: energia, vento\nlow: Betz") == (["energia", "vento"], ["Betz"])


def test_hippo_rag_spreads_from_question_entities(make_deps):
    deps, rec = make_deps()
    out = run("hippo_rag", deps)
    assert out.diagnostics["linked"]["Betz"]["by"] == "name" and out.diagnostics["query_nodes"] >= 1
    assert {c.source for c in out.contexts} == {"hipporag:ppr"} and "Betz" in out.context.text
    assert out.usage.calls_by_task == {"kg_extract": out.usage.calls_by_task["kg_extract"], "entities": 1, "answer": 1}
    deps, _ = make_deps()
    lost = run("hippo_rag", deps, query=Query("q", "qual a capital da mongólia?"))
    assert "dense retrieval was used" in lost.warnings[0] and {c.source for c in lost.contexts} == {"dense"}
    chain = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0)]
    rank = hippo_rag.pagerank(5, chain, np.array([1.0, 0, 0, 0, 0]), 0.5, 40)
    assert rank[0] > rank[1] > rank[2] > rank[3] > rank[4] == 0 and abs(rank.sum() - 1.0) < 1e-6
    rows = np.array([[1.0, 0.0], [0.99, 0.14], [0.0, 1.0]])
    assert hippo_rag.synonym_edges(rows / np.linalg.norm(rows, axis=1, keepdims=True), 0.9, 5) == [(0, 1)]


def test_self_rag_critiques_candidates(make_deps, monkeypatch):
    deps, _ = make_deps()
    out = run("self_rag", deps)
    calls, candidates = out.usage.calls_by_task, out.diagnostics["candidates"]
    assert calls["needs_retrieval"] == 1 and calls["relevance"] == out.diagnostics["graded"] == 6
    assert calls["answer"] == calls["support"] == len(candidates) <= 3
    assert candidates == sorted(candidates, key=lambda c: -c["score"])
    assert out.contexts[0].chunk.id == candidates[0]["chunk_id"] and out.answer.text.endswith("[1]")
    assert "emulates reflection tokens" in out.warnings[0]
    assert self_rag.parse_critique("Support: Partial.\nUSEFUL: 5 de 5")[:2] == (0.5, 1.0)
    assert self_rag.parse_critique("não sei")[:2] == (0.0, 0.0)
    monkeypatch.setitem(mock._RULES, "needs_retrieval", lambda v: "não")
    deps, rec = make_deps()
    direct = run("self_rag", deps)
    assert not direct.contexts and direct.context.text == "" and not direct.diagnostics["retrieved"]
    assert direct.usage.calls_by_task == {"needs_retrieval": 1, "answer_direct": 1}
    validate_result(direct, registry.get("self_rag").spec)
    deps, _ = make_deps()
    assert run("self_rag", deps, adaptive_retrieval=False).diagnostics["retrieved"]


def test_rank_rag_scores_a_larger_pool(make_deps):
    deps, _ = make_deps(reranker="llm")
    out = run("rank_rag", deps)
    assert out.diagnostics["candidates"] == 12 and out.usage.calls_by_task == {"rank_passages": 1, "answer": 1}
    scores = [c.score for c in out.contexts]
    assert scores == sorted(scores, reverse=True) and {c.source for c in out.contexts} == {"rank_rag"}
    assert out.diagnostics["dropped_below_min"] > 0
    deps, _ = make_deps()
    pointwise = run("rank_rag", deps, scoring="pointwise", candidates_factor=2)
    assert pointwise.usage.calls_by_task["rank_passages"] == 6
    assert [c.chunk.id for c in pointwise.contexts][0] == [c.chunk.id for c in out.contexts][0]
    assert rank_rag.parse_scores("[1]: 7,5\n2 - 11\n9: 3\nlixo", 2) == {0: 7.5, 1: 10.0}


def test_adaptive_rag_routes_by_complexity(make_deps):
    deps, _ = make_deps()
    single = run("adaptive_rag", deps)
    assert single.diagnostics["route"] == "single_step" and single.usage.calls_by_task == {"complexity": 1, "answer": 1}
    deps, _ = make_deps(retrieval_mode="bm25")
    multi = run("adaptive_rag", deps, query=MULTI, k=4)
    assert multi.diagnostics["route"] == "multi_step" and multi.diagnostics["hops"] == 2
    assert "Betz" in multi.context.text and "Fernando de Noronha" in multi.context.text
    deps, _ = make_deps()
    trivial = run("adaptive_rag", deps, query=Query("q", "Olá?"))
    assert trivial.diagnostics["route"] == "no_retrieval" and not trivial.contexts
    validate_result(trivial, registry.get("adaptive_rag").spec)
    deps, _ = make_deps()
    assert run("adaptive_rag", deps, query=Query("q", "Olá?"), allow_no_retrieval=False).contexts


def test_multi_hop_chains_sub_questions(make_deps):
    deps, rec = make_deps(retrieval_mode="bm25")
    out = run("multi_hop", deps, query=MULTI, k=4)
    trace = out.diagnostics["trace"]
    assert [t["hop"] for t in trace] == [1, 2] and all(t["answer"] for t in trace)
    assert out.usage.calls_by_task == {"next_hop": 3, "hop_answer": 2, "answer": 1}
    assert [e["payload"]["query"] for e in rec.events if e["kind"] == "retrieval"] == [t["sub_question"] for t in trace]
    assert "Betz" in out.context.text and "Fernando de Noronha" in out.context.text
    second = next(e["payload"] for e in rec.events if e["kind"] == "request" and e["payload"]["task"] == "next_hop"
                  and "Etapa 2" in e["payload"]["user"])
    assert trace[0]["answer"][:30] in second["user"], "the next hop is written from the facts already found"
    deps, _ = make_deps()
    assert run("multi_hop", deps, max_hops=1).diagnostics["hops"] == 1


def test_hybrid_rag_and_rag_fusion(make_deps):
    deps, _ = make_deps(retrieval_mode="dense")
    assert {c.source for c in run("hybrid_rag", deps).contexts} == {"rrf"}
    deps, _ = make_deps()
    assert {c.source for c in run("hybrid_rag", deps, fusion="weighted").contexts} == {"hybrid"}
    deps, rec = make_deps()
    fused = run("rag_fusion", deps, n_queries=3)
    assert len(fused.diagnostics["queries"]) == 3 and fused.diagnostics["queries"][0] == Q.text
    assert sum(1 for e in rec.events if e["kind"] == "retrieval") == 3
    assert {c.source for c in fused.contexts} == {"rrf"} and fused.usage.calls_by_task == {"multi_queries": 1, "answer": 1}


def test_agentic_plans_and_calls_tools(make_deps):
    deps, rec = make_deps()
    out = run("agentic", deps)
    assert out.diagnostics["tools_used"] == ["search", "keyword_search", "read_more", "finish"]
    assert out.diagnostics["plan"] and out.diagnostics["tool_mode"] == "native" and not out.warnings
    assert out.usage.calls_by_task == {"agent_plan": 1, "agent_step": 4, "answer": 1}
    steps = [e["payload"] for e in rec.events if e["payload"].get("task") == "agent_step"]
    assert steps[0]["tools"] == ["search", "keyword_search", "read_more", "finish"]
    assert steps[1]["tool_calls"] == [{"name": "search", "arguments": {"query": Q.text}}]
    modes = [e["payload"]["mode"] for e in rec.events if e["kind"] == "retrieval"]
    assert modes == ["dense", "bm25", "agentic:read_more"]
    assert "[1] " in steps[2]["user"], "passages found so far are shown to the agent as numbered notes"
    deps, _ = make_deps()
    short = run("agentic", deps, max_steps=1, planning=False)
    assert short.diagnostics["tools_used"] == ["search"] and "agent_plan" not in short.usage.calls_by_task


def test_agentic_falls_back_to_the_text_protocol(make_deps):
    deps, _ = make_deps()
    text = run("agentic", deps, tool_mode="text")
    assert text.diagnostics["tool_mode"] == "text" and text.usage.calls_by_task["agent_step_text"] == 4
    assert text.diagnostics["tools_used"] == ["search", "keyword_search", "read_more", "finish"]
    deps, _ = make_deps()

    def rejected(task, tools, **variables):
        raise ProviderError("this model does not support tools", status_code=400)
    deps.ask_tool = rejected
    out = run("agentic", deps)
    assert "rejected native tool calling" in out.warnings[0] and out.diagnostics["tool_mode"] == "text"
    assert agentic.parse_text_choice('ok: {"tool": "search", "arguments": {"query": "x"}}').arguments == {"query": "x"}
    assert agentic.parse_text_choice("SEARCH: x").name == "" and agentic.parse_text_choice('{"tool": "rm"}').name == ""


def test_long_context_sends_whole_documents(make_deps, store):
    deps, _ = make_deps()
    out = run("long_context", deps)
    assert {c.source for c in out.contexts} == {"long_context:document"} and out.diagnostics["whole_documents"] >= 1
    for item in out.contexts:
        text = store.document_text(item.chunk.document_id)
        assert text[item.chunk.char_start:item.chunk.char_end] == item.chunk.text == text
    assert out.context.chars > 1000 and "Betz" in out.context.text and out.usage.calls_by_task == {"answer": 1}
    assert registry.get("long_context").spec.ignored_axes() == ("max_context_chars",)
    deps, _ = make_deps()
    tight = run("long_context", deps, context_chars=700, max_documents=1, min_window_chars=100)
    window = tight.contexts[0]
    assert len(tight.contexts) == 1 and not window.chunk.metadata["whole_document"] and tight.context.chars <= 700
    text = store.document_text(window.chunk.document_id)
    assert text[window.chunk.char_start:window.chunk.char_end] == window.chunk.text and "Betz" in window.chunk.text


def test_hierarchical_restricts_chunks_to_the_best_documents(make_deps, store):
    deps, rec = make_deps()
    out = run("hierarchical", deps, top_documents=1)
    chosen = [d["document_id"] for d in out.diagnostics["documents"]]
    assert chosen == ["energia-eolica"] and {c.chunk.document_id for c in out.contexts} == {"energia-eolica"}
    assert out.diagnostics["built_now"] and out.usage.calls_by_task["summarize"] == out.diagnostics["documents_in_index"] == 3
    retrieval = next(e["payload"] for e in rec.events if e["kind"] == "retrieval")
    assert retrieval["filters"] == {"document_id": ["energia-eolica"]}
    deps, _ = make_deps()
    again = run("hierarchical", deps, top_documents=1)
    assert not again.diagnostics["built_now"] and "summarize" not in again.usage.calls_by_task
    deps, _ = make_deps()
    mean = run("hierarchical", deps, document_vector="mean", top_documents=2)
    assert mean.usage.calls_by_task == {"answer": 1} and len(mean.diagnostics["documents"]) == 2
    deps, _ = make_deps()
    scoped = registry.get("hierarchical").run(
        TechniqueRequest(Q, k=3, filters={"document_id": "energia-solar"}), deps)
    assert {c.chunk.document_id for c in scoped.contexts} == {"energia-solar"}, "the request filter still applies"


def test_recomp_compresses_and_keeps_what_was_retrieved(make_deps, monkeypatch):
    deps, _ = make_deps()
    out = run("recomp", deps)
    assert out.usage.calls_by_task == {"recomp_summary": 1, "answer": 1}
    assert out.contexts[-1].source == "recomp:summary" and out.context.chunk_ids == ("recomp:summary",)
    assert [c.source for c in out.contexts[:-1]] == ["dense"] * 3, "retrieved chunks stay available to the metrics"
    assert out.citations == validate_result(out, registry.get("recomp").spec).citations
    assert [c["chunk_id"] for c in out.citations] == ["recomp:summary"] and out.citations[0]["n"] == 1
    assert out.context.chars < out.diagnostics["chars_before"] and 0 < out.diagnostics["compression_ratio"] < 1
    deps, _ = make_deps()
    picked = run("recomp", deps, compressor="extractive", n_sentences=2)
    assert picked.usage.calls_by_task == {"answer": 1} and picked.diagnostics["chars_after"] < picked.diagnostics[
        "chars_before"]
    assert all(c.chunk.metadata.get("compressed") for c in picked.contexts) and "Betz" in picked.context.text
    monkeypatch.setitem(mock._RULES, "recomp_summary", lambda v: "NONE.")
    deps, _ = make_deps()
    empty = run("recomp", deps)
    assert empty.diagnostics["answered_without_context"] and empty.context.text == "" and len(empty.contexts) == 3
    assert empty.usage.calls_by_task == {"recomp_summary": 1, "answer_direct": 1}
    validate_result(empty, registry.get("recomp").spec)
    deps, _ = make_deps()
    kept = run("recomp", deps, selective=False)
    assert "uncompressed passages were used" in kept.warnings[1] and "Betz" in kept.context.text


def test_speculative_rag_drafts_from_diverse_subsets(make_deps):
    deps, _ = make_deps(reranker="llm")
    out = run("speculative_rag", deps)
    drafts = out.diagnostics["drafts"]
    assert out.diagnostics["candidates"] == 6 and out.diagnostics["clusters"] == 3 and 1 < len(drafts) <= 3
    assert out.usage.calls_by_task == {"answer": len(drafts), "confidence": len(drafts)}, "the run's reranker is unused"
    assert all(len(d["chunks"]) == 3 for d in drafts) and len({tuple(d["chunks"]) for d in drafts}) == len(drafts)
    chosen = next(d for d in drafts if d["chosen"])
    assert chosen["score"] == max(d["score"] for d in drafts)
    assert [c.chunk.id for c in out.contexts] == chosen["chunks"] and set(out.context.chunk_ids) <= set(chosen["chunks"])
    labels = np.array([0, 0, 1, 1, 2])
    pool = out.contexts[:1] * 5
    assert speculative_rag.subsets(pool, labels, 2), "wrapping around small clusters never fails"
    assert speculative_rag.parse_score("0,8") == 0.8 and speculative_rag.parse_score("nota 7") == 0.7
    assert speculative_rag.parse_score("sem número") == 0.0

