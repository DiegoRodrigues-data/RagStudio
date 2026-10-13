"""Multi-Hop RAG: the question is answered through a chain of sub-questions, each retrieved and answered in turn.

Related work: Trivedi et al., "Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive
Multi-Step Questions" (IRCoT, ACL 2023).

At each hop the LLM reads the facts found so far and writes the next sub-question (or stops), the index is searched
for it, and the LLM answers that sub-question in one sentence from the retrieved passages. The intermediate answer
is what lets the next hop ask about something the original question never names. The final answer is generated
once, over the passages of every hop.

It differs from `iterative`, which re-answers the whole question each round and searches for what is missing, and
from `decomposition`, which writes all sub-questions up front, before anything is retrieved.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate
from ._multihop import hop_chain

SPEC = TechniqueSpec(
    name="multi_hop", title="Multi-Hop RAG", stage="orchestration", version="1.0.0", family="iterative",
    description="Chain of sub-questions: each hop is written from the facts found so far, retrieved and answered.",
    params={"max_hops": Param(3, "maximum sub-questions (the model may stop earlier)"),
            "hop_passages": Param(3, "passages read to answer each sub-question")},
    reference="https://arxiv.org/abs/2212.10509", origin="new",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    chunks, trace = hop_chain(deps, request, params["max_hops"], params["hop_passages"])
    answer, context = generate(deps, request.query.text, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context, {"hops": len(trace), "trace": trace})
