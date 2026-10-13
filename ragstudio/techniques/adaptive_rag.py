"""Adaptive RAG: the question is classified by complexity and routed to the cheapest strategy that can answer it.

Reference: Jeong et al., "Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through
Question Complexity" (NAACL 2024).

Routes, as in the paper:
- A: no retrieval, the model answers from its own knowledge;
- B: single-step retrieval (the same pipeline as `naive`);
- C: multi-step retrieval (the hop chain of `multi_hop`).

Difference from the paper: the complexity classifier there is a small model trained on automatically labelled
questions; here it is a zero-shot prompt to the run's LLM, which costs one extra call per question.
`allow_no_retrieval=false` sends route A to B, for studies in which every answer must come from the corpus.
"""
from __future__ import annotations

import re

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import answer_without_retrieval, finish, generate, pool_size, select
from ._multihop import hop_chain

SPEC = TechniqueSpec(
    name="adaptive_rag", title="Adaptive RAG", stage="orchestration", version="1.0.0", family="routing",
    description="Classify the question's complexity and route it to no retrieval, single-step or multi-step "
                "retrieval.",
    params={"allow_no_retrieval": Param(True, "let simple questions be answered without retrieval (route A)"),
            "max_hops": Param(3, "maximum sub-questions on the multi-step route"),
            "hop_passages": Param(3, "passages read to answer each sub-question on the multi-step route")},
    reference="https://arxiv.org/abs/2403.14403", origin="new",
)
_LABEL = re.compile(r"\b([ABC])\b")


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    warnings: list[str] = []
    with deps.stage("control"):
        raw = deps.ask("complexity", query=question).strip()
    match = _LABEL.search(raw.upper())
    label = match.group(1) if match else "B"
    if not match:
        warnings.append(f"the classifier answered '{raw[:40]}' instead of A, B or C; single-step retrieval was used")
    route = "B" if label == "A" and not params["allow_no_retrieval"] else label
    diagnostics: dict = {"complexity": label, "route": {"A": "no_retrieval", "B": "single_step", "C": "multi_step"}[route]}
    if route == "A":
        answer, context = answer_without_retrieval(deps, question)
        return finish(SPEC, deps, answer, [], context, diagnostics, warnings)
    if route == "C":
        chunks, trace = hop_chain(deps, request, params["max_hops"], params["hop_passages"])
        diagnostics.update({"hops": len(trace), "trace": trace})
    else:
        with deps.stage("retrieval"):
            pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters)
        chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context, diagnostics, warnings)
