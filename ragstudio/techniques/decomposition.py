"""Query decomposition: split the question into sub-questions, retrieve for each, answer the original question.

Ported from `ragkit.rag_decomposition`.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, merge_pool, parse_lines, select

SPEC = TechniqueSpec(
    name="decomposition", title="Query Decomposition", stage="query", version="1.0.0", family="query",
    description="Decompose the question into sub-questions and pool what each one retrieves.",
    params={"n_subquestions": Param(4, "maximum number of sub-questions"),
            "include_original": Param(True, "also retrieve with the original question")},
    reference="https://arxiv.org/abs/2410.12837", origin="ragkit.rag_decomposition", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("query_transform"):
        subquestions = parse_lines(deps.ask("decompose", query=question, n=params["n_subquestions"]),
                                   params["n_subquestions"])
    queries = list(dict.fromkeys(([question] if params["include_original"] or not subquestions else [])
                                 + subquestions))
    per_query = max(2, request.k // 2)
    with deps.stage("retrieval"):
        pool = merge_pool(*[deps.retrieve(q, per_query, filters=request.filters) for q in queries])
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"subquestions": subquestions, "queries": len(queries), "per_query_k": per_query,
                   "pool": len(pool)})
