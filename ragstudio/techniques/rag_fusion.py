"""RAG-Fusion: several LLM-written versions of the question, one ranking each, fused by Reciprocal Rank Fusion.

Reference: Rackauckas, "RAG-Fusion: a New Take on Retrieval-Augmented Generation" (2024).

It differs from `multi_query` in the fusion: there the pool keeps the best score of each chunk by default, here
the rankings are always fused by rank, which rewards chunks that several queries agree on.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, parse_lines, select
from ..retrieval.fusion import rrf

SPEC = TechniqueSpec(
    name="rag_fusion", title="RAG-Fusion", stage="query", version="1.0.0", family="query",
    description="Generate reformulations of the question, retrieve for each and fuse the rankings by RRF.",
    params={"n_queries": Param(4, "queries searched, the original included"),
            "rrf_k": Param(60, "rank constant of the fusion")},
    reference="https://arxiv.org/abs/2402.03367", origin="new",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    n = max(1, params["n_queries"])
    with deps.stage("query_transform"):
        generated = parse_lines(deps.ask("multi_queries", query=question, n=n), n) if n > 1 else []
        queries = list(dict.fromkeys([question, *generated]))[:n]
    with deps.stage("retrieval"):
        rankings = [deps.retrieve(q, request.k * 2, filters=request.filters) for q in queries]
        pool = rrf(rankings, request.k * 2, params["rrf_k"])
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    final = {c.chunk.id for c in chunks}
    return finish(SPEC, deps, answer, chunks, context,
                  {"queries": queries, "pool": len(pool),
                   "contributions": [{"query": q, "in_final": sum(1 for i in r if i.chunk.id in final)}
                                     for q, r in zip(queries, rankings, strict=True)]})
