"""RankRAG (prototype): the same LLM ranks the retrieved passages and then answers from the best ones.

Reference: Yu et al., "RankRAG: Unifying Context Ranking with Retrieval-Augmented Generation in LLMs"
(NeurIPS 2024).

A larger candidate set is retrieved (k x `candidates_factor`), the run's LLM scores how useful each passage is for
the question, the top k are kept and the answer is generated from them.

Prototype scope, stated plainly: the paper instruction-tunes ONE model on ranking and generation together and
reads the relevance of each passage from its token probabilities; here an off-the-shelf LLM is prompted for a 0-10
score. `scoring="batch"` scores all candidates in one call; `scoring="pointwise"` uses one call per passage, as the
paper does. The run's own reranker is not applied: ranking is this technique's job.
"""
from __future__ import annotations

import re

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, rerank_ranks

SPEC = TechniqueSpec(
    name="rank_rag", title="RankRAG", stage="post_retrieval", ignores=("reranker",), version="0.1.0", family="ranking",
    description="The generator LLM scores a larger set of retrieved passages, keeps the best k and answers.",
    params={"candidates_factor": Param(4, "passages retrieved and scored = k x this factor"),
            "scoring": Param("batch", "batch: one call for all passages; pointwise: one call per passage",
                             ("batch", "pointwise")),
            "min_score": Param(1.0, "passages scored below this (0-10) are dropped"),
            "passage_chars": Param(800, "characters of each passage shown to the scorer")},
    reference="https://arxiv.org/abs/2407.02485", origin="new", status="prototype",
)
_LINE = re.compile(r"^\s*\[?(\d+)\]?\s*[:\-–]\s*(\d+(?:[.,]\d+)?)", re.M)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def parse_scores(raw: str, n: int) -> dict[int, float]:
    """`number: score` lines -> {0-based position: score clipped to 0..10}."""
    scores: dict[int, float] = {}
    for number, score in _LINE.findall(raw):
        position = int(number) - 1
        if 0 <= position < n and position not in scores:
            scores[position] = max(0.0, min(10.0, float(score.replace(",", "."))))
    return scores


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question, k = request.query.text, request.k
    warnings = ["rank_rag prompts a general LLM for scores instead of a ranking-tuned model (see module docstring)"]
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, k * max(1, params["candidates_factor"]), filters=request.filters)
    texts = [item.chunk.text[:params["passage_chars"]] for item in pool]
    scores: dict[int, float] = {}
    with deps.stage("rerank"):
        if params["scoring"] == "batch" and texts:
            scores = parse_scores(deps.ask("rank_passages", query=question, passages=texts), len(texts))
        else:
            for position, text in enumerate(texts):
                raw = deps.ask("rank_passages", query=question, passages=[text])
                found = parse_scores(raw, 1).get(0)
                if found is None and (number := _NUMBER.search(raw)):
                    found = max(0.0, min(10.0, float(number.group(0).replace(",", "."))))
                if found is not None:
                    scores[position] = found
    if not scores and pool:
        warnings.append("the scorer returned no readable score; the retrieval order was kept")
        chunks = rerank_ranks(pool[:k])
    else:
        order = sorted(scores, key=lambda i: (-scores[i], pool[i].rank))
        kept = [i for i in order if scores[i] >= params["min_score"]] or order[:1]
        chunks = [pool[i].with_rank(rank, score=scores[i] / 10.0, source="rank_rag")
                  for rank, i in enumerate(kept[:k], 1)]
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"scoring": params["scoring"], "candidates": len(pool), "scored": len(scores),
                   "dropped_below_min": sum(1 for s in scores.values() if s < params["min_score"]),
                   "scores": [{"chunk_id": pool[i].chunk.id, "score": scores[i], "retrieval_rank": pool[i].rank}
                              for i in sorted(scores, key=lambda i: -scores[i])[:k * 2]]}, warnings)
