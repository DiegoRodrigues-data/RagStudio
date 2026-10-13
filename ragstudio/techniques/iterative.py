"""Iterative retrieval with gap queries: retrieve -> answer -> ask what is missing -> retrieve again.

Related work: Jiang et al., "Active Retrieval Augmented Generation" (FLARE), EMNLP 2023. This is the simpler
round-based variant ported from `ragkit.rag_iterative`, not token-level active retrieval.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import Answer, Context, RetrievedChunk
from ..core.pipeline import finish, generate, merge_pool, select

SPEC = TechniqueSpec(
    name="iterative", title="Iterative RAG", stage="orchestration", version="1.0.0", family="iterative",
    description="Rounds of retrieval and answering; each round searches for what the partial answer lacks.",
    params={"rounds": Param(2, "number of retrieve/answer rounds")},
    reference="https://arxiv.org/abs/2305.06983", origin="ragkit.rag_iterative", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    rounds = max(1, params["rounds"])
    pool: list[RetrievedChunk] = []
    chunks: list[RetrievedChunk] = []
    answer, context = Answer(""), Context("", (), 0, False)
    current = question
    trace = []
    for n in range(1, rounds + 1):
        with deps.stage("retrieval"):
            pool = merge_pool(pool, deps.retrieve(current, request.k, filters=request.filters))
        chunks = select(deps, question, pool, request.k)
        answer, context = generate(deps, question, chunks, request.max_context_chars)
        trace.append({"round": n, "query": current, "pool": len(pool), "answer_chars": len(answer.text)})
        if n < rounds:
            with deps.stage("query_transform"):
                current = deps.ask("gap_query", query=question, answer=answer.text).strip() or question
    return finish(SPEC, deps, answer, chunks, context, {"rounds": rounds, "trace": trace})
