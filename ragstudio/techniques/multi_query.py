"""Multi-Query / query expansion: several reformulations, one pooled result.

Reference: Gupta et al., "A Comprehensive Survey of Retrieval-Augmented Generation (RAG)", 2024 (query expansion).
Ported from `ragkit.rag_multi_query`; adds RRF as an alternative to the max-score pool.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, merge_pool, parse_lines, select
from ..retrieval.fusion import rrf

SPEC = TechniqueSpec(
    name="multi_query", title="Multi-Query RAG", stage="query", version="1.0.0", family="query",
    description="Generate reformulations of the question, retrieve for each and pool the results.",
    params={"n_queries": Param(4, "total queries, including the original one"),
            "fusion": Param("max", "how to pool: best score per chunk, or reciprocal rank fusion",
                            choices=("max", "rrf"))},
    reference="https://arxiv.org/abs/2410.12837", origin="ragkit.rag_multi_query", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    n = max(1, params["n_queries"])
    with deps.stage("query_transform"):
        generated = parse_lines(deps.ask("multi_queries", query=question, n=n), n) if n > 1 else []
        queries = list(dict.fromkeys([question, *generated]))[:n]
    with deps.stage("retrieval"):
        rankings = [deps.retrieve(q, request.k, filters=request.filters) for q in queries]
        pool = rrf(rankings, request.k * len(queries)) if params["fusion"] == "rrf" else merge_pool(*rankings)
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    final = {c.chunk.id for c in chunks}
    contributions = [{"query": q, "retrieved": len(r), "in_final": sum(1 for i in r if i.chunk.id in final)}
                     for q, r in zip(queries, rankings, strict=True)]
    return finish(SPEC, deps, answer, chunks, context,
                  {"queries": queries, "fusion": params["fusion"], "pool": len(pool),
                   "contributions": contributions})
