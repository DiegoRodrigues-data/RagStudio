"""GraphRAG: a knowledge graph with community reports, queried locally (entities) or globally (map-reduce).

Reference: Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (2024).

Indexing, once per index (cached next to it; the cost lands on the first question, see `built_now`):
1. the LLM extracts typed entities and relations with descriptions from every chunk (shared with LightRAG and
   HippoRAG through `_kg.py`);
2. hierarchical communities are detected on the entity graph (Louvain; the paper uses Leiden);
3. the LLM writes one report per community, at every level.

Querying:
- `mode="local"`: entities matched by name or by embedding similarity select text units (chunks) through the graph;
  that ranking is fused with dense retrieval by RRF (`dense_fusion`, an addition of this implementation: set it to
  false for the paper's pure local search), and the report of the best-matching community joins the context;
- `mode="global"`: map-reduce over community reports. Each of the most similar reports is asked for the points
  that answer the question, with a 0-100 helpfulness score (map); the best-scored points become the context of the
  final answer (reduce).

Not implemented: claim (covariate) extraction, summarizing sub-community reports when a community exceeds the input
budget (entities are prioritized by degree and cut instead), DRIFT search, incremental indexing.
"""
from __future__ import annotations

from typing import Any

from ...core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ...core.models import RetrievedChunk
from ...core.pipeline import finish, generate, rerank_ranks, select, synthetic_chunk
from ...retrieval.fusion import rrf
from ...stores.graph import KnowledgeGraph, louvain
from .. import _kg

SPEC = TechniqueSpec(
    name="graph_rag", title="GraphRAG", stage="indexing",
    ignores=lambda p: ("retrieval_mode", "reranker") if p["mode"] == "global" else ("retrieval_mode",),
    version="1.0.0", family="graph",
    description="Knowledge graph with community reports: local search through entities, or global map-reduce "
                "over the reports.",
    params={"mode": Param("local", "local: entities and their text units; global: map-reduce over reports",
                          ("local", "global")),
            "top_entities": Param(10, "entities matched to the question by embedding similarity (local)"),
            "dense_fusion": Param(True, "fuse the graph ranking with dense retrieval by RRF (local)"),
            "include_report": Param(True, "add the report of the best-matching community to the context (local)"),
            "community_level": Param(0, "0 = coarsest communities; higher = finer (global)"),
            "global_reports": Param(8, "community reports asked for points (global, one LLM call each)"),
            "min_community_size": Param(2, "communities with fewer entities get no report"),
            "report_input_chars": Param(6000, "characters of entities and relations sent to the report writer"),
            **_kg.KG_PARAMS},
    requires=("embedder", "llm", "index:aux"),
    reference="https://arxiv.org/abs/2404.16130", origin="new",
)


def build_reports(deps: TechniqueDeps, graph: KnowledgeGraph, min_size: int, input_chars: int) -> list[dict[str, Any]]:
    """One report per community of every level. `level` 0 is the coarsest, as in the paper."""
    adjacency = graph.adjacency()
    degree = {key: sum(links.values()) for key, links in adjacency.items()}
    levels = list(reversed(louvain(adjacency)))
    reports: list[dict[str, Any]] = []
    written: dict[tuple[str, ...], dict[str, Any]] = {}  # a community unchanged between levels is written once
    for level, membership in enumerate(levels):
        groups: dict[str, list[str]] = {}
        for entity, community in membership.items():
            groups.setdefault(community, []).append(entity)
        for community in sorted(groups):
            members = sorted(groups[community], key=lambda k: (-degree.get(k, 0.0), k))
            if len(members) < min_size:
                continue
            signature = tuple(sorted(members))
            if signature not in written:
                inside = set(members)
                edges = sorted((e for e in graph.relations.values() if e["source"] in inside and e["target"] in inside),
                               key=lambda e: (-e["weight"], e["source"], e["target"]))
                entity_lines, relation_lines, used = [], [], 0
                for text in (graph.entity_text(k) for k in members):
                    if used + len(text) > input_chars * 0.6:
                        break
                    entity_lines.append(text)
                    used += len(text)
                for text in (graph.relation_text(e) for e in edges):
                    if used + len(text) > input_chars:
                        break
                    relation_lines.append(text)
                    used += len(text)
                raw = deps.ask("community_report", entities=entity_lines, relations=relation_lines).strip()
                title, _, body = raw.partition("\n")
                chunk_ids = list(dict.fromkeys(cid for k in members for cid in graph.entities[k]["chunks"]))
                written[signature] = {"title": title.strip("# ").strip(), "text": raw, "body": body.strip() or raw,
                                      "entities": members, "document_id": _kg.main_document(deps, chunk_ids)}
            if written[signature]["text"]:
                reports.append({**written[signature], "id": f"graphrag:L{level}:{community}", "level": level})
    return reports


def load_reports(deps: TechniqueDeps, graph: KnowledgeGraph, key: str, params: dict[str, Any]) -> tuple[list, bool]:
    name = f"graphrag_{key[3:]}_{params['min_community_size']}_{params['report_input_chars']}"
    cached = deps.store.aux_load(name)
    if cached is not None:
        return cached, False
    with deps.stage("index_build"):
        reports = build_reports(deps, graph, params["min_community_size"], params["report_input_chars"])
        deps.store.aux_save(name, reports)
    return reports, True


def match_entities(deps: TechniqueDeps, graph: KnowledgeGraph, key: str, question: str, vector: list[float],
                   limit: int) -> dict[str, float]:
    """Entity -> weight: 1.0 for a name present in the question, cosine similarity otherwise."""
    keys = list(graph.entities)
    matrix = _kg.vectors(deps, key, "entities", [graph.entity_text(k) for k in keys])
    weights = {keys[i]: score for i, score in _kg.top(_kg.similarities(matrix, vector), limit)}
    weights.update({k: 1.0 for k in graph.match(question)})
    return weights


def local_search(deps: TechniqueDeps, graph: KnowledgeGraph, reports: list[dict[str, Any]], key: str,
                 request: TechniqueRequest, params: dict[str, Any]) -> tuple[list[RetrievedChunk], dict[str, Any]]:
    question, k = request.query.text, request.k
    with deps.stage("retrieval"):
        vector = deps.embed([question])[0]
        weights = match_entities(deps, graph, key, question, vector, params["top_entities"])
        scores: dict[str, float] = {}
        for entity, weight in weights.items():
            for chunk_id in graph.entities[entity]["chunks"]:
                scores[chunk_id] = scores.get(chunk_id, 0.0) + weight
        for edge in graph.relations.values():  # a chunk stating a relation between two matched entities counts more
            if edge["source"] in weights and edge["target"] in weights:
                bonus = 0.5 * min(weights[edge["source"]], weights[edge["target"]])
                for chunk_id in edge["chunks"]:
                    scores[chunk_id] = scores.get(chunk_id, 0.0) + bonus
        via_graph = _kg.ranked_chunks(deps, scores, k * 2, "graphrag:local", request.filters)
        deps.log_retrieval(question, "graphrag:local", via_graph)
        dense = (deps.retrieve(question, k * 2, mode="dense", query_vector=vector, filters=request.filters)
                 if params["dense_fusion"] or not via_graph else [])
        pool = rrf([via_graph, dense], k * 2) if via_graph and dense else via_graph or dense
        report = None
        if params["include_report"] and k >= 3 and weights:
            finest = max((r["level"] for r in reports), default=0)
            overlap = [(sum(weights.get(e, 0.0) for e in r["entities"]), r) for r in reports if r["level"] == finest]
            best = max(overlap, key=lambda item: (item[0], item[1]["id"]), default=(0.0, None))
            report = best[1] if best[0] > 0 else None
    chunks = select(deps, question, pool, k - 1 if report else k)
    if report:
        chunks.append(synthetic_chunk(report["id"], report["document_id"] or (chunks[0].chunk.document_id if chunks else ""),
                                      report["text"], 0.0, len(chunks) + 1, "graphrag:community",
                                      level=report["level"], entities=len(report["entities"])))
    dense_ids = {c.chunk.id for c in dense}
    return chunks, {"question_entities": [graph.label(e) for e in sorted(weights, key=lambda e: (-weights[e], e))][:10],
                    "graph_candidates": len(via_graph), "community_report": report["id"] if report else None,
                    "from_graph_only": sum(1 for c in chunks if c.chunk.index >= 0 and c.chunk.id not in dense_ids)}


def global_search(deps: TechniqueDeps, reports: list[dict[str, Any]], key: str, request: TechniqueRequest,
                  params: dict[str, Any]) -> tuple[list[RetrievedChunk], dict[str, Any]]:
    question = request.query.text
    deepest = max((r["level"] for r in reports), default=0)
    level = min(max(0, params["community_level"]), deepest)
    candidates = [r for r in reports if r["level"] == level]
    with deps.stage("retrieval"):
        vector = deps.embed([question])[0]
        matrix = _kg.vectors(deps, key, f"reports:L{level}", [r["text"] for r in candidates])
        nearest = _kg.top(_kg.similarities(matrix, vector), params["global_reports"], minimum=-1.0)
    points: list[tuple[int, dict[str, Any], str]] = []
    with deps.stage("compression"):  # the map step: each report is reduced to the points that answer the question
        for position, _ in nearest:
            report = candidates[position]
            raw = deps.ask("community_points", query=question, report=report["text"]).strip()
            head, _, body = raw.partition("\n")
            digits = "".join(c for c in head if c.isdigit())
            score = min(100, int(digits)) if digits else 0
            if score > 0 and body.strip():
                points.append((score, report, body.strip()))
    points.sort(key=lambda item: (-item[0], item[1]["id"]))
    chunks = [synthetic_chunk(report["id"], report["document_id"], f"{report['title']}\n{body}", score / 100.0, rank,
                              "graphrag:community", level=level, entities=len(report["entities"]))
              for rank, (score, report, body) in enumerate(points[:request.k], 1)]
    deps.log_retrieval(question, "graphrag:global", chunks)
    return chunks, {"community_level": level, "reports_at_level": len(candidates), "reports_mapped": len(nearest),
                    "reports_with_points": len(points)}


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    warnings: list[str] = []
    graph, key, built_graph = _kg.load_graph(deps, params)
    reports, built_reports = load_reports(deps, graph, key, params)
    mode = params["mode"]
    chunks: list[RetrievedChunk] = []
    details: dict[str, Any] = {}
    if mode == "global":
        chunks, details = global_search(deps, reports, key, request, params)
        if not chunks:
            warnings.append("no community report helped with this question; local search was used instead")
            mode = "local (fallback)"
    if not chunks:
        chunks, local = local_search(deps, graph, reports, key, request, params)
        details = {**details, **local}
    answer, context = generate(deps, question, rerank_ranks(chunks), request.max_context_chars)
    return finish(SPEC, deps, answer, rerank_ranks(chunks), context,
                  {"mode": mode, "graph_entities": len(graph.entities), "graph_relations": len(graph.relations),
                   "communities": len(reports), "built_now": built_graph or built_reports,
                   "graph_built_now": built_graph, **details}, warnings)
