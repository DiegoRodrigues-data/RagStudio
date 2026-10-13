"""RAG-EVO (Evolutive Introspective RAG), v4: diverse retrieval, generation, confidence score, iterative recovery.

Reference: RAG-EVO chapter in "Advances in Information Retrieval" (Springer),
https://link.springer.com/chapter/10.1007/978-3-032-05176-9_27
Ported from `ragkit.rag_evo`. The per-round JSONL log of the original is now `diagnostics["traces"]`, persisted by
the experiment runner with the rest of the evidence.
"""
from __future__ import annotations

from ...core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ...core.models import Answer, Context, RetrievedChunk
from ...core.pipeline import finish, generate, merge_pool, select
from . import confidence as conf

SPEC = TechniqueSpec(
    name="rag_evo", title="RAG-EVO", stage="orchestration",
    ignores=lambda p: ("retrieval_mode",) if p["use_mmr"] else (),
    version="4.0.0", family="iterative",
    description="Rounds of (MMR) retrieval and answering scored by a confidence heuristic; below the threshold a "
                "gap query drives another round and the best-scored answer wins.",
    params={"rounds": Param(2, "maximum rounds"),
            "confidence_threshold": Param(0.6, "stop as soon as a round reaches this confidence"),
            "confidence_mode": Param("composite", "how confidence is computed", choices=conf.MODES),
            "alpha": Param(0.34, "weight of answer length"), "beta": Param(0.33, "weight of lexical entropy"),
            "gamma": Param(0.33, "weight of context coverage"),
            "confidence_target_chars": Param(800, "answer length that saturates the length term"),
            "use_mmr": Param(True, "retrieve with MMR instead of the run's retrieval mode"),
            "mmr_lambda": Param(0.6, "MMR relevance/diversity trade-off")},
    reference="https://link.springer.com/chapter/10.1007/978-3-032-05176-9_27", origin="ragkit.rag_evo",
    status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    p = SPEC.resolve(request.params)
    question = request.query.text
    weights = {"alpha": p["alpha"], "beta": p["beta"], "gamma": p["gamma"]}
    retrieval = {"mode": "mmr", "lambda_": p["mmr_lambda"], "k_candidates": max(40, request.k * 4)} \
        if p["use_mmr"] else {}
    pool: list[RetrievedChunk] = []
    best: tuple[float, Answer, list[RetrievedChunk], Context] = (-1.0, Answer(""), [], Context("", (), 0, False))
    current = question
    traces = []
    for n in range(1, max(1, p["rounds"]) + 1):
        with deps.stage("retrieval"):
            pool = merge_pool(pool, deps.retrieve(current, request.k * 2, filters=request.filters, **retrieval))
        chunks = select(deps, question, pool, request.k)
        answer, context = generate(deps, question, chunks, request.max_context_chars)
        with deps.stage("control"):
            score = conf.evaluate(p["confidence_mode"], deps.ask, question, answer.text, context.text,
                                  [c.chunk.text for c in chunks], weights, p["confidence_target_chars"])
        traces.append({"round": n, "query": current, "pool": len(pool), **score})
        if score["confidence"] > best[0]:
            best = (score["confidence"], answer, chunks, context)
        if score["confidence"] >= p["confidence_threshold"] or n == p["rounds"]:
            break
        with deps.stage("query_transform"):
            current = deps.ask("gap_query", query=question, answer=answer.text).strip() or question
    confidence, answer, chunks, context = best
    return finish(SPEC, deps, answer, chunks, context,
                  {"best_confidence": confidence, "rounds_run": len(traces), "threshold": p["confidence_threshold"],
                   "needs_review": confidence < p["confidence_threshold"], "confidence_mode": p["confidence_mode"],
                   "traces": traces})
