"""Hybrid RAG: lexical (BM25) and semantic (dense) retrieval combined, then one grounded answer.

The run's retrieval mode is ignored on purpose, as in `mmr_rag`: this technique IS the hybrid retrieval, so it can
be compared with `naive` on the same index whatever mode the run uses. `fusion="rrf"` combines the two rankings by
Reciprocal Rank Fusion (Cormack et al., SIGIR 2009); `fusion="weighted"` sums max-normalized scores.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, pool_size, select

SPEC = TechniqueSpec(
    name="hybrid_rag", title="Hybrid RAG", stage="retrieval", ignores=("retrieval_mode",), version="1.0.0", family="basic",
    description="Retrieve with BM25 and dense search combined (RRF or weighted sum) and answer.",
    params={"fusion": Param("rrf", "how the lexical and dense rankings are combined", ("rrf", "weighted")),
            "dense_weight": Param(0.7, "weight of the dense score when fusion is weighted"),
            "rrf_k": Param(60, "rank constant when fusion is rrf")},
    reference="https://doi.org/10.1145/1571941.1572114", origin="new",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    options = {"rrf_k": params["rrf_k"]} if params["fusion"] == "rrf" else {"dense_weight": params["dense_weight"]}
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters,
                             mode="rrf" if params["fusion"] == "rrf" else "hybrid", **options)
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context, {"fusion": params["fusion"], "pool": len(pool)})
