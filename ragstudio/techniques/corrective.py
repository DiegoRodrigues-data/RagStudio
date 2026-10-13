"""Corrective RAG (CRAG-like): grade each retrieved chunk, drop the irrelevant ones, re-query when too few remain.

Related work: Yan et al., "Corrective Retrieval Augmented Generation" (2024) and Asai et al., "Self-RAG" (ICLR
2024). This implementation keeps the retrieve -> grade -> correct loop over the local index only: the web-search
branch of CRAG and the reflection tokens of Self-RAG are NOT implemented.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import RetrievedChunk
from ..core.pipeline import finish, generate, parse_lines, rerank_ranks

SPEC = TechniqueSpec(
    name="corrective", title="Corrective RAG", stage="orchestration", ignores=("reranker",), version="1.0.0", family="self-evaluation",
    description="LLM grades the relevance of each retrieved chunk; irrelevant ones are dropped and, when too few "
                "survive, the query is rewritten and retrieval repeated.",
    params={"candidates_factor": Param(2, "chunks graded = k * factor"),
            "min_relevant": Param(1, "below this many relevant chunks a corrective retrieval is triggered"),
            "max_chunk_chars": Param(1500, "characters of each chunk shown to the grader")},
    reference="https://arxiv.org/abs/2401.15884", origin="new", status="implemented",
)
_YES = ("sim", "yes", "relevante", "relevant")


def grade(deps: TechniqueDeps, question: str, items: list[RetrievedChunk],
          max_chars: int) -> tuple[list[RetrievedChunk], list[dict]]:
    kept, decisions = [], []
    for item in items:
        verdict = deps.ask("relevance", query=question, text=item.chunk.text[:max_chars]).strip().lower()
        relevant = verdict.startswith(_YES)
        decisions.append({"chunk_id": item.chunk.id, "relevant": relevant, "verdict": verdict[:20]})
        if relevant:
            kept.append(item)
    return kept, decisions


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    warnings: list[str] = []
    with deps.stage("retrieval"):
        first = deps.retrieve(question, request.k * max(1, params["candidates_factor"]), filters=request.filters)
    with deps.stage("control"):
        kept, decisions = grade(deps, question, first, params["max_chunk_chars"])
    action, rewritten = "correct", None
    if len(kept) < params["min_relevant"]:
        action = "ambiguous" if kept else "incorrect"
        with deps.stage("query_transform"):
            alternatives = [q for q in parse_lines(deps.ask("multi_queries", query=question, n=2), 2) if q != question]
            rewritten = alternatives[0] if alternatives else None
        if rewritten:
            seen = {c.chunk.id for c in first}
            with deps.stage("retrieval"):
                second = [c for c in deps.retrieve(rewritten, request.k * 2, filters=request.filters)
                          if c.chunk.id not in seen]
            with deps.stage("control"):
                more, extra = grade(deps, question, second, params["max_chunk_chars"])
            kept, decisions = kept + more, decisions + extra
    if not kept:
        warnings.append("no chunk was graded relevant; falling back to the ungraded top-k")
        kept = first
    chunks = rerank_ranks(sorted(kept, key=lambda c: (-c.score, c.chunk.id))[:request.k])
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"action": action, "graded": len(decisions),
                   "relevant": sum(1 for d in decisions if d["relevant"]), "rewritten_query": rewritten,
                   "decisions": decisions}, warnings)
