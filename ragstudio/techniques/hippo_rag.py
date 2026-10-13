"""HippoRAG: associative retrieval by Personalized PageRank over a knowledge graph.

Reference: Gutiérrez et al., "HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models"
(NeurIPS 2024).

Indexing reuses the triples of the graph shared with GraphRAG and LightRAG (`_kg.py`). On top of it, synonym edges
link entities whose embeddings are similar, so different spellings of the same thing are connected.

Querying:
1. the LLM extracts the named entities of the question;
2. each one is linked to a graph node, by name or by nearest embedding;
3. Personalized PageRank spreads probability from those nodes through the graph. Each query node is weighted by
   its node specificity (the inverse of the number of chunks mentioning it), as in the paper;
4. a chunk scores the sum of the probabilities of the entities it mentions.

A single PageRank pass reaches passages several hops away from the question, without iterating over the LLM.
When no entity of the question can be linked, dense retrieval is used and the result carries a warning.

Not implemented: the passage nodes and the recognition-memory triple filter added by HippoRAG 2.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, parse_lines, select
from ..core.text import normalize
from ..stores.graph import KnowledgeGraph
from . import _kg

SPEC = TechniqueSpec(
    name="hippo_rag", title="HippoRAG", stage="indexing", ignores=("retrieval_mode",), version="1.0.0", family="graph",
    description="Personalized PageRank from the question's entities over a knowledge graph with synonym edges.",
    params={"damping": Param(0.5, "probability of following a graph edge instead of restarting at a query node"),
            "synonym_threshold": Param(0.8, "cosine similarity above which two entities get a synonym edge"),
            "max_synonyms": Param(5, "synonym edges kept per entity"),
            "link_threshold": Param(0.3, "minimum similarity to link a question entity to a node by embedding"),
            "max_query_entities": Param(8, "entities extracted from the question"),
            "iterations": Param(30, "PageRank power iterations"),
            **_kg.KG_PARAMS},
    requires=("embedder", "llm", "index:aux"),
    reference="https://arxiv.org/abs/2405.14831", origin="new",
)


def synonym_edges(matrix: np.ndarray, threshold: float, limit: int, block: int = 512) -> list[tuple[int, int]]:
    """Pairs (i < j) of rows with cosine >= threshold, at most `limit` per row, computed block by block."""
    pairs: set[tuple[int, int]] = set()
    for start in range(0, len(matrix), block):
        with np.errstate(all="ignore"):
            sims = matrix[start:start + block] @ matrix.T
        for offset, row in enumerate(sims):
            i = start + offset
            row[i] = -1.0
            for j in np.argsort(-row, kind="stable")[:limit]:
                if row[j] >= threshold:
                    pairs.add((min(i, int(j)), max(i, int(j))))
    return sorted(pairs)


def pagerank(n: int, edges: list[tuple[int, int, float]], personalization: np.ndarray, damping: float,
             iterations: int) -> np.ndarray:
    """Personalized PageRank by power iteration on an undirected weighted graph given as (i, j, weight) triples."""
    if not edges:
        return personalization
    src = np.array([e[0] for e in edges] + [e[1] for e in edges])
    dst = np.array([e[1] for e in edges] + [e[0] for e in edges])
    weight = np.array([e[2] for e in edges] * 2, dtype=np.float64)
    out = np.bincount(src, weights=weight, minlength=n)
    share = weight / out[src]
    dangling = out == 0
    rank = personalization.copy()
    for _ in range(iterations):
        spread = np.bincount(dst, weights=rank[src] * share, minlength=n)
        spread += rank[dangling].sum() * personalization  # a node without edges returns its mass to the query nodes
        rank = (1.0 - damping) * personalization + damping * spread
    return rank


def link_entities(deps: TechniqueDeps, graph: KnowledgeGraph, keys: list[str], matrix: np.ndarray, names: list[str],
                  threshold: float) -> dict[str, dict[str, Any]]:
    """Question entity -> graph node, by exact name, by contained name, then by nearest embedding."""
    position = {key: i for i, key in enumerate(keys)}
    linked: dict[str, dict[str, Any]] = {}
    pending: list[str] = []
    for name in names:
        key = normalize(name)
        match = key if key in position else next(iter(graph.match(name)), None)
        if match is not None:
            linked[name] = {"node": match, "similarity": 1.0, "by": "name"}
        elif key:
            pending.append(name)
    if pending and len(keys):
        for name, vector in zip(pending, deps.embed(pending), strict=True):
            best = _kg.top(_kg.similarities(matrix, vector), 1, minimum=threshold)
            if best:
                linked[name] = {"node": keys[best[0][0]], "similarity": round(best[0][1], 4), "by": "embedding"}
    return linked


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question, k = request.query.text, request.k
    warnings: list[str] = []
    graph, key, built_now = _kg.load_graph(deps, params)
    keys = list(graph.entities)
    position = {entity: i for i, entity in enumerate(keys)}
    with deps.stage("query_transform"):
        names = parse_lines(deps.ask("entities", text=question), params["max_query_entities"])
    with deps.stage("retrieval"):
        matrix = _kg.vectors(deps, key, "entity_names", [graph.label(e) for e in keys])
        cache = f"hippo_{key[3:]}_{params['synonym_threshold']}_{params['max_synonyms']}"
        synonyms = deps.store.aux_load(cache)
        if synonyms is None:
            synonyms = synonym_edges(matrix.copy(), params["synonym_threshold"], params["max_synonyms"])
            deps.store.aux_save(cache, synonyms)
        linked = link_entities(deps, graph, keys, matrix, names, params["link_threshold"])
        nodes = sorted({item["node"] for item in linked.values()})
        ranking = []
        if nodes:
            personalization = np.zeros(len(keys))
            for node in nodes:  # node specificity: rarer entities pull harder
                personalization[position[node]] = 1.0 / max(1, len(graph.entities[node]["chunks"]))
            personalization /= personalization.sum()
            edges = [(position[e["source"]], position[e["target"]], float(e["weight"]))
                     for e in graph.relations.values()]
            edges += [(int(i), int(j), 1.0) for i, j in synonyms]
            rank = pagerank(len(keys), edges, personalization, params["damping"], params["iterations"])
            scores: dict[str, float] = {}
            for entity, probability in zip(keys, rank, strict=True):
                if probability > 0:
                    for chunk_id in graph.entities[entity]["chunks"]:
                        scores[chunk_id] = scores.get(chunk_id, 0.0) + float(probability)
            ranking = _kg.ranked_chunks(deps, scores, _pool(deps, k), "hipporag:ppr", request.filters)
            deps.log_retrieval(question, "hipporag:ppr", ranking)
        if not ranking:
            warnings.append("no entity of the question was found in the graph; dense retrieval was used instead")
            ranking = deps.retrieve(question, _pool(deps, k), filters=request.filters)
    chunks = select(deps, question, ranking, k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"question_entities": names, "linked": {name: {**item, "node": graph.label(item["node"])}
                                                          for name, item in linked.items()},
                   "query_nodes": len(nodes), "graph_entities": len(keys), "graph_relations": len(graph.relations),
                   "synonym_edges": len(synonyms), "built_now": built_now}, warnings)


def _pool(deps: TechniqueDeps, k: int) -> int:
    return k * 3 if deps.has_reranker else k
