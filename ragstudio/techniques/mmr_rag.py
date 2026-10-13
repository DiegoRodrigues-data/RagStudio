"""Naive RAG over MMR retrieval: relevance balanced with diversity to avoid redundant context.

Reference: Carbonell & Goldstein, "The Use of MMR, Diversity-Based Reranking for Reordering Documents and
Producing Summaries", SIGIR 1998. Ported from `ragkit.mmr` / `make_duckdb_vector_mmr_retriever`.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate

SPEC = TechniqueSpec(
    name="mmr_rag", title="MMR RAG", stage="retrieval", ignores=("retrieval_mode", "reranker"), version="1.0.0", family="diversity",
    description="Retrieve with Maximal Marginal Relevance (relevance vs. diversity) and answer.",
    params={"lambda_": Param(0.6, "1.0 = pure relevance, 0.0 = pure diversity"),
            "k_candidates": Param(40, "dense candidates considered by MMR")},
    reference="https://dl.acm.org/doi/10.1145/290941.291025", origin="ragkit.mmr", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("retrieval"):
        # MMR already produces the final order; a reranker would undo the diversity, so it is not applied here
        chunks = deps.retrieve(question, request.k, mode="mmr", filters=request.filters,
                               lambda_=params["lambda_"], k_candidates=params["k_candidates"])
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"lambda": params["lambda_"], "k_candidates": params["k_candidates"],
                   "documents_in_context": len({c.chunk.document_id for c in chunks})})
