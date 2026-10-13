"""Naive RAG: retrieve top-k, optionally rerank, answer from the retrieved context.

Reference: Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS 2020.
Ported from `ragkit.rag_naive`. `retrieval_mode` covers the basic retrieval variants (dense, BM25, hybrid, RRF)
without one module per variant.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, pool_size, select
from ..retrieval import MODES

SPEC = TechniqueSpec(
    name="naive", title="Naive RAG", stage="retrieval", ignores=lambda p: ("retrieval_mode",) if p["retrieval_mode"] else (),
    version="1.0.0", family="basic",
    description="Retrieve top-k chunks for the question and answer from them.",
    params={"retrieval_mode": Param(None, "override the run's retrieval mode", choices=(None, *MODES))},
    reference="https://arxiv.org/abs/2005.11401", origin="ragkit.rag_naive", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), mode=params["retrieval_mode"],
                             filters=request.filters)
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context, {"retrieval_mode": params["retrieval_mode"],
                                                        "pool": len(pool)})
