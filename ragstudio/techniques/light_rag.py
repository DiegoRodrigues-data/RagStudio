"""LightRAG: dual-level retrieval over a knowledge graph, combined with vector retrieval.

Reference: Guo et al., "LightRAG: Simple and Fast Retrieval-Augmented Generation" (2024).

Indexing reuses the entity and relation graph shared with GraphRAG and HippoRAG (`_kg.py`, one LLM call per chunk,
once per index); entities and relations are embedded from their names and descriptions.

Querying:
1. the LLM extracts low-level keywords (specific entities and terms) and high-level keywords (themes);
2. low level: the low-level keywords are matched to ENTITIES; their chunks and strongest relations are collected;
3. high level: the high-level keywords are matched to RELATIONS; their chunks and endpoint entities are collected;
4. `mode`: `local` (2), `global` (3), `hybrid` (2 + 3) or `mix` (2 + 3 + vector retrieval over chunks, fused by
   RRF), which is the default as in the reference implementation;
5. the context holds the text chunks plus one passage listing the matched entities and relations.

Not implemented: incremental graph updates and the LLM-based merging of duplicate entity descriptions (descriptions
are kept as extracted, at most four per entity).
"""
from __future__ import annotations

from typing import Any

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import RetrievedChunk
from ..core.pipeline import finish, generate, rerank_ranks, select, synthetic_chunk
from ..retrieval.fusion import rrf
from ..stores.graph import KnowledgeGraph
from . import _kg

SPEC = TechniqueSpec(
    name="light_rag", title="LightRAG", stage="indexing",
    ignores=lambda p: () if p["mode"] == "mix" else ("retrieval_mode",),
    version="1.0.0", family="graph",
    description="Dual-level graph retrieval: low-level keywords match entities, high-level keywords match "
                "relations, optionally mixed with vector retrieval.",
    params={"mode": Param("mix", "which retrieval levels are used", ("local", "global", "hybrid", "mix")),
            "top_entities": Param(10, "entities matched to the low-level keywords"),
            "top_relations": Param(10, "relations matched to the high-level keywords"),
            "graph_context_chars": Param(1500, "size of the passage listing matched entities and relations"),
            **_kg.KG_PARAMS},
    requires=("embedder", "llm", "index:aux"),
    reference="https://arxiv.org/abs/2410.05779", origin="new",
)
HEADERS = {"pt": ("Entidades", "Relações"), "en": ("Entities", "Relations")}


def parse_keywords(raw: str) -> tuple[list[str], list[str]]:
    levels: dict[str, list[str]] = {"HIGH": [], "LOW": []}
    for line in raw.splitlines():
        head, _, rest = line.partition(":")
        level = head.strip().upper().lstrip("-* ")
        if level in levels:
            levels[level] = [w.strip() for w in rest.split(",") if w.strip()]
    return levels["HIGH"], levels["LOW"]


def low_level(deps: TechniqueDeps, graph: KnowledgeGraph, key: str, keywords: list[str],
              limit: int) -> tuple[dict[str, float], dict[str, float], list[dict[str, Any]]]:
    """Keywords -> entities -> (entity weights, chunk scores, the entities' strongest relations)."""
    keys = list(graph.entities)
    matrix = _kg.vectors(deps, key, "entities", [graph.entity_text(k) for k in keys])
    vector = deps.embed([", ".join(keywords)])[0]
    weights = {keys[i]: score for i, score in _kg.top(_kg.similarities(matrix, vector), limit)}
    weights.update({k: 1.0 for k in graph.match(" , ".join(keywords))})
    scores: dict[str, float] = {}
    for entity, weight in weights.items():
        for chunk_id in graph.entities[entity]["chunks"]:
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight
    edges = [e for e in graph.relations.values() if e["source"] in weights or e["target"] in weights]
    edges.sort(key=lambda e: (-(weights.get(e["source"], 0.0) + weights.get(e["target"], 0.0)), -e["weight"],
                              e["source"], e["target"]))
    return weights, scores, edges[:limit]


def high_level(deps: TechniqueDeps, graph: KnowledgeGraph, key: str, keywords: list[str],
               limit: int) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Keywords -> relations -> (matched relations, chunk scores)."""
    edges = list(graph.relations.values())
    matrix = _kg.vectors(deps, key, "relations", [graph.relation_text(e) for e in edges])
    vector = deps.embed([", ".join(keywords)])[0]
    matched = [(edges[i], score) for i, score in _kg.top(_kg.similarities(matrix, vector), limit)]
    scores: dict[str, float] = {}
    for edge, score in matched:
        for chunk_id in edge["chunks"]:
            scores[chunk_id] = scores.get(chunk_id, 0.0) + score
    return [edge for edge, _ in matched], scores


def graph_passage(graph: KnowledgeGraph, entities: list[str], edges: list[dict[str, Any]], language: str,
                  max_chars: int) -> str:
    entity_title, relation_title = HEADERS.get(language, HEADERS["en"])
    lines = [f"{entity_title}:"] + [f"- {graph.entity_text(k)}" for k in entities]
    lines += [f"{relation_title}:"] + [f"- {graph.relation_text(e)}" for e in edges]
    out, used = [], 0
    for line in lines:
        if used + len(line) > max_chars:
            break
        out.append(line)
        used += len(line) + 1
    return "\n".join(out)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question, k, mode = request.query.text, request.k, params["mode"]
    warnings: list[str] = []
    graph, key, built_now = _kg.load_graph(deps, params)
    with deps.stage("query_transform"):
        high, low = parse_keywords(deps.ask("lightrag_keywords", query=question))
        if not high and not low:
            warnings.append("keyword extraction returned nothing; the question itself was used at both levels")
        high, low = high or [question], low or [question]
    entities: dict[str, float] = {}
    edges: list[dict[str, Any]] = []
    rankings: list[list[RetrievedChunk]] = []
    with deps.stage("retrieval"):
        if mode in ("local", "hybrid", "mix") and graph.entities:
            entities, scores, entity_edges = low_level(deps, graph, key, low, params["top_entities"])
            edges += entity_edges
            rankings.append(_kg.ranked_chunks(deps, scores, k * 2, "lightrag:local", request.filters))
            deps.log_retrieval(", ".join(low), "lightrag:local", rankings[-1])
        if mode in ("global", "hybrid", "mix") and graph.relations:
            relation_edges, scores = high_level(deps, graph, key, high, params["top_relations"])
            edges += [e for e in relation_edges if e not in edges]
            for edge in relation_edges:
                for endpoint in (edge["source"], edge["target"]):
                    entities.setdefault(endpoint, 0.0)
            rankings.append(_kg.ranked_chunks(deps, scores, k * 2, "lightrag:global", request.filters))
            deps.log_retrieval(", ".join(high), "lightrag:global", rankings[-1])
        rankings = [r for r in rankings if r]
        if mode == "mix" or not rankings:
            if mode != "mix":
                warnings.append("the graph matched nothing for this question; vector retrieval was used instead")
            rankings.append(deps.retrieve(question, k * 2, filters=request.filters))
        pool = rrf(rankings, k * 2) if len(rankings) > 1 else rankings[0]
    ordered = sorted(entities, key=lambda e: (-entities[e], e))
    passage = graph_passage(graph, ordered, edges, deps.language, params["graph_context_chars"]) \
        if k >= 3 and (ordered or edges) else ""
    chunks = select(deps, question, pool, k - 1 if passage else k)
    if passage:
        chunks.append(synthetic_chunk("lightrag:graph", chunks[0].chunk.document_id if chunks else "", passage, 0.0,
                                      len(chunks) + 1, "lightrag:graph", entities=len(ordered), relations=len(edges)))
    chunks = rerank_ranks(chunks)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"mode": mode, "high_level_keywords": high, "low_level_keywords": low,
                   "matched_entities": [graph.label(e) for e in ordered][:10], "matched_relations": len(edges),
                   "graph_entities": len(graph.entities), "graph_relations": len(graph.relations),
                   "built_now": built_now}, warnings)
