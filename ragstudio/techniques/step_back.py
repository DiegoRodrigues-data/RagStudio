"""Step-back prompting: also retrieve with a more general question about the underlying concept.

Reference: Zheng et al., "Take a Step Back: Evoking Reasoning via Abstraction in Large Language Models", ICLR 2024.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, merge_pool, select

SPEC = TechniqueSpec(
    name="step_back", title="Step-Back Prompting", stage="query", version="1.0.0", family="query",
    description="Retrieve with the question and with an LLM-written, more general 'step-back' question.",
    params={"step_back_share": Param(0.5, "fraction of k retrieved with the step-back question")},
    reference="https://arxiv.org/abs/2310.06117", origin="new", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("query_transform"):
        general = deps.ask("step_back", query=question).strip() or question
    k_general = max(1, round(request.k * params["step_back_share"]))
    with deps.stage("retrieval"):
        specific = deps.retrieve(question, request.k, filters=request.filters)
        abstract = deps.retrieve(general, k_general, filters=request.filters) if general != question else []
        pool = merge_pool(specific, abstract)
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    only_abstract = {c.chunk.id for c in abstract} - {c.chunk.id for c in specific}
    return finish(SPEC, deps, answer, chunks, context,
                  {"step_back_question": general, "pool": len(pool),
                   "from_step_back_only": sum(1 for c in chunks if c.chunk.id in only_abstract)})
