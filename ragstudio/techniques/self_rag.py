"""Self-RAG (prototype): retrieve on demand, answer from each passage, and let self-critique pick the answer.

Reference: Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection"
(ICLR 2024).

What the paper does with special reflection tokens emitted by a fine-tuned model is done here with separate
prompts to the run's LLM:
- Retrieve: the model decides whether the question needs retrieval at all (`adaptive_retrieval`);
- ISREL: each retrieved passage is graded relevant or not;
- one candidate answer is generated from EACH of the best relevant passages, in isolation;
- ISSUP and ISUSE: each candidate is graded for support by its passage (full, partial, none) and for usefulness
  (1 to 5); the candidate with the best weighted critique is the answer.

Prototype scope, stated plainly: no fine-tuned generator or critic, so the critique is a prompted judgement and not
a token probability; candidates are whole answers, not the paper's segment-level beam search. It costs many calls:
with defaults, 1 + 2k gradings + 3 answers + 3 critiques.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import Answer
from ..core.pipeline import answer_without_retrieval, finish, format_context, rerank_ranks

SPEC = TechniqueSpec(
    name="self_rag", title="Self-RAG", stage="orchestration", ignores=("reranker",), version="0.1.0", family="self-evaluation",
    description="Decide whether to retrieve, answer from each relevant passage and keep the answer its own "
                "critique rates best.",
    params={"adaptive_retrieval": Param(True, "let the model skip retrieval when it judges it unnecessary"),
            "candidates_factor": Param(2, "passages retrieved and graded = k x this factor"),
            "candidates": Param(3, "relevant passages that each generate a candidate answer"),
            "support_weight": Param(1.0, "weight of the support critique (ISSUP)"),
            "usefulness_weight": Param(0.5, "weight of the usefulness critique (ISUSE)"),
            "max_chunk_chars": Param(1500, "characters of each passage shown to the graders")},
    reference="https://arxiv.org/abs/2310.11511", origin="new", status="prototype",
)
_YES = ("sim", "yes", "s", "y")
_SUPPORT = {"full": 1.0, "fully": 1.0, "total": 1.0, "partial": 0.5, "partially": 0.5, "parcial": 0.5}
_FIELD = re.compile(r"^\s*(SUPPORT|USEFUL)\s*:\s*(.+)$", re.I | re.M)


def parse_critique(raw: str) -> tuple[float, float, dict[str, str]]:
    """(support 0..1, usefulness 0..1, raw fields). Anything unreadable counts as no support / least useful."""
    fields = {name.upper(): value.strip() for name, value in _FIELD.findall(raw)}
    words = fields.get("SUPPORT", "").lower().split()
    support = _SUPPORT.get(words[0].strip(".,"), 0.0) if words else 0.0
    digits = re.search(r"[1-5]", fields.get("USEFUL", ""))
    usefulness = (int(digits.group(0)) - 1) / 4 if digits else 0.0
    return support, usefulness, fields


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question, k = request.query.text, request.k
    warnings = ["self_rag emulates reflection tokens with prompts (see module docstring)"]
    if params["adaptive_retrieval"]:
        with deps.stage("control"):
            verdict = deps.ask("needs_retrieval", query=question).strip().lower()
        if verdict and not verdict.startswith(_YES):
            answer, context = answer_without_retrieval(deps, question)
            return finish(SPEC, deps, answer, [], context, {"retrieved": False, "retrieve_verdict": verdict[:20]},
                          warnings)
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, k * max(1, params["candidates_factor"]), filters=request.filters)
    relevant = []
    with deps.stage("control"):
        for item in pool:
            verdict = deps.ask("relevance", query=question, text=item.chunk.text[:params["max_chunk_chars"]])
            if verdict.strip().lower().startswith(_YES):
                relevant.append(item)
    if not relevant:
        warnings.append("no passage was graded relevant; the ungraded top passages were used")
    sources = (relevant or pool)[:max(1, params["candidates"])]
    candidates: list[dict[str, Any]] = []
    for item in sources:
        with deps.stage("context"):
            single = format_context([item.with_rank(1)], request.max_context_chars)
        with deps.stage("generation"):
            text = deps.ask("answer", query=question, context=single.text).strip()
        with deps.stage("control"):
            support, usefulness, fields = parse_critique(
                deps.ask("support", query=question, answer=text, passage=item.chunk.text[:params["max_chunk_chars"]]))
        candidates.append({"item": item, "text": text, "support": support, "usefulness": usefulness,
                           "fields": fields, "score": params["support_weight"] * support
                           + params["usefulness_weight"] * usefulness})
    candidates.sort(key=lambda c: (-c["score"], -c["item"].score, c["item"].chunk.id))
    used = {c["item"].chunk.id for c in candidates}
    ordered = [c["item"] for c in candidates] + [i for i in (relevant or pool) if i.chunk.id not in used]
    chunks = rerank_ranks(ordered[:k])  # the winning passage is [1], which is what the winning answer cites
    with deps.stage("context"):
        context = format_context(chunks, request.max_context_chars)
    best = candidates[0]
    return finish(SPEC, deps, Answer(text=best["text"], raw_response=best["text"], model=deps.llm_model), chunks,
                  context,
                  {"retrieved": True, "graded": len(pool), "relevant": len(relevant),
                   "candidates": [{"chunk_id": c["item"].chunk.id, "support": c["support"],
                                   "usefulness": round(c["usefulness"], 2), "score": round(c["score"], 3),
                                   "critique": c["fields"]} for c in candidates]}, warnings)
