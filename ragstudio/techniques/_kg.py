"""Knowledge-graph plumbing shared by GraphRAG, LightRAG and HippoRAG (not a technique: the registry skips `_`).

The three techniques read the SAME extracted graph, so an index pays for entity and relation extraction once (one
LLM call per chunk), whichever of them runs first. The graph is cached next to the index, keyed by LLM, language
and the two extraction parameters; entity and relation vectors are kept in memory for the process and come from
the embedding cache on later runs.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from ..core.contract import Param, TechniqueDeps
from ..core.hashing import sha256_text
from ..core.models import RetrievedChunk
from ..stores.base import matches
from ..stores.graph import KnowledgeGraph
from ._vectors import similarities, top, unit_rows, vectors

__all__ = ["KG_PARAMS", "graph_key", "load_graph", "main_document", "ranked_chunks", "similarities", "top",
           "unit_rows", "vectors"]

KG_PARAMS = {"max_entities_per_chunk": Param(12, "entities kept per chunk when the graph is extracted"),
             "entity_input_chars": Param(2000, "characters of each chunk sent to the extractor")}


def graph_key(deps: TechniqueDeps, params: dict[str, Any]) -> str:
    return "kg_" + sha256_text(f"{deps.llm_model}|{deps.language}|{params['max_entities_per_chunk']}|"
                               f"{params['entity_input_chars']}")[:12]


def load_graph(deps: TechniqueDeps, params: dict[str, Any]) -> tuple[KnowledgeGraph, str, bool]:
    """(graph, cache key, built_now). Building is timed as `index_build` and lands on the question that needs it."""
    key = graph_key(deps, params)
    cached = deps.store.aux_load(key)
    if cached is not None:
        return KnowledgeGraph.from_dict(cached), key, False
    graph = KnowledgeGraph()
    with deps.stage("index_build"):
        for chunk in deps.store.all_chunks():
            raw = deps.ask("kg_extract", text=chunk.text[:params["entity_input_chars"]],
                           max_entities=params["max_entities_per_chunk"])
            graph.add_extraction(chunk.id, raw, params["max_entities_per_chunk"])
        deps.store.aux_save(key, graph.to_dict())
    return graph, key, True


def ranked_chunks(deps: TechniqueDeps, scores: dict[str, float], limit: int, source: str,
                  filters: dict[str, Any] | None = None) -> list[RetrievedChunk]:
    """Chunk scores computed by a graph -> ranked `RetrievedChunk`s (ties broken by chunk id)."""
    order = sorted(scores, key=lambda cid: (-scores[cid], cid))
    found = {c.id: c for c in deps.store.get(order)}
    kept = [cid for cid in order if cid in found and matches(found[cid], {}, filters)][:limit]
    return [RetrievedChunk(found[cid], float(scores[cid]), rank, source) for rank, cid in enumerate(kept, 1)]


def main_document(deps: TechniqueDeps, chunk_ids: list[str]) -> str:
    """The document most of `chunk_ids` come from: where a synthetic passage about them is attributed."""
    counts = Counter(c.document_id for c in deps.store.get(chunk_ids))
    return counts.most_common(1)[0][0] if counts else ""
