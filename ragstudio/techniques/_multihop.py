"""Chained retrieval shared by Multi-Hop RAG and by the multi-step route of Adaptive RAG (not a technique)."""
from __future__ import annotations

from typing import Any

from ..core.contract import TechniqueDeps, TechniqueRequest
from ..core.models import RetrievedChunk
from ..core.pipeline import format_context, interleave, merge_pool, select


def hop_chain(deps: TechniqueDeps, request: TechniqueRequest, max_hops: int,
              hop_passages: int) -> tuple[list[RetrievedChunk], list[dict[str, Any]]]:
    """Up to `max_hops` rounds of: write the next sub-question from the facts found so far, retrieve for it, answer
    it briefly. Returns the final chunks (every hop contributes its best passages first) and the trace."""
    question = request.query.text
    facts: list[str] = []
    rankings: list[list[RetrievedChunk]] = []
    trace: list[dict[str, Any]] = []
    for hop in range(1, max(1, max_hops) + 1):
        with deps.stage("query_transform"):
            sub = deps.ask("next_hop", query=question, facts="\n".join(f"- {f}" for f in facts) or "-", hop=hop,
                           max_hops=max_hops).strip()
        done = not sub or sub.upper().lstrip("-* ").startswith("DONE")
        if done and hop > 1:
            break
        sub = question if done else sub.splitlines()[0].strip()
        with deps.stage("retrieval"):
            found = deps.retrieve(sub, request.k, filters=request.filters)
        with deps.stage("control"):
            evidence = format_context(found[:hop_passages], max(400, request.max_context_chars // 2))
            partial = deps.ask("hop_answer", query=sub, context=evidence.text).strip() if found else ""
        if partial:
            facts.append(f"{sub} {partial}")
        rankings.append(found)
        trace.append({"hop": hop, "sub_question": sub, "answer": partial[:200], "retrieved": len(found)})
        if done:
            break
    if deps.has_reranker:
        return select(deps, question, merge_pool(*rankings), request.k), trace
    return interleave(rankings, request.k), trace
