"""Speculative RAG (prototype): several drafts from diverse subsets of the evidence, and a verifier picks one.

Reference: Wang et al., "Speculative RAG: Enhancing Retrieval Augmented Generation through Drafting" (2024).

1. A larger set of passages is retrieved and clustered by content (k-means on their embeddings).
2. Each draft takes ONE passage from every cluster, so every draft sees a different, diverse slice of the evidence
   and no draft reads everything.
3. An answer is drafted from each subset.
4. Each draft is scored for how well it is supported by its subset and answers the question; the best one wins.

Prototype scope, stated plainly: the paper uses a small fine-tuned specialist model to draft, in parallel, and a
larger generalist model to verify from token probabilities. A run here has one LLM, so the same model drafts and
verifies, sequentially, and the verification is a prompted 0-1 score. The run's reranker is not applied.
"""
from __future__ import annotations

import re

import numpy as np

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import Answer, RetrievedChunk
from ..core.pipeline import finish, format_context, rerank_ranks
from ..core.seeds import rng
from . import _vectors

SPEC = TechniqueSpec(
    name="speculative_rag", title="Speculative RAG", stage="orchestration", ignores=("reranker",), version="0.1.0",
    family="self-evaluation",
    description="Draft an answer from each of several diverse subsets of the retrieved passages and keep the draft "
                "a verification step scores best.",
    params={"n_drafts": Param(3, "drafts generated (one answer and one verification call each)"),
            "docs_per_draft": Param(3, "passages in each draft's subset = number of clusters"),
            "candidates_factor": Param(2, "passages retrieved = k x this factor")},
    reference="https://arxiv.org/abs/2407.08223", origin="new", status="prototype",
)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def kmeans(matrix: np.ndarray, k: int, seed: int, iterations: int = 20) -> np.ndarray:
    """Cosine k-means over unit rows; deterministic for a seed."""
    centers = matrix[rng(seed).choice(len(matrix), size=k, replace=False)].copy()
    labels = np.zeros(len(matrix), dtype=int)
    for _ in range(iterations):
        with np.errstate(all="ignore"):  # numpy/Accelerate emits spurious matmul warnings on macOS arm64
            labels = np.argmax(matrix @ centers.T, axis=1)
        for c in range(k):
            members = matrix[labels == c]
            if len(members):
                center = members.mean(axis=0)
                centers[c] = center / (np.linalg.norm(center) or 1.0)
    return labels


def subsets(pool: list[RetrievedChunk], labels: np.ndarray, n_drafts: int) -> list[list[RetrievedChunk]]:
    """Draft j takes the j-th best passage of every cluster (wrapping around); identical subsets are dropped."""
    clusters = [[item for item, label in zip(pool, labels, strict=True) if label == c] for c in sorted(set(labels))]
    out: list[list[RetrievedChunk]] = []
    for j in range(n_drafts):
        subset = sorted((cluster[j % len(cluster)] for cluster in clusters), key=lambda c: (-c.score, c.chunk.id))
        if [c.chunk.id for c in subset] not in [[c.chunk.id for c in s] for s in out]:
            out.append(subset)
    return out


def parse_score(raw: str) -> float:
    match = _NUMBER.search(raw)
    value = float(match.group(0).replace(",", ".")) if match else 0.0
    return max(0.0, min(1.0, value if value <= 1 else value / 10 if value <= 10 else value / 100))


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question, k = request.query.text, request.k
    warnings = ["speculative_rag drafts and verifies with the same LLM (see module docstring)"]
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, k * max(1, params["candidates_factor"]), filters=request.filters)
        n_clusters = max(1, min(params["docs_per_draft"], k, len(pool)))
        if len(pool) > n_clusters:
            matrix = _vectors.unit_rows([deps.store.embedding(c.chunk.id) for c in pool]).astype(np.float64)
            labels = kmeans(matrix, n_clusters, deps.seed)
        else:
            labels = np.arange(len(pool))
        groups = subsets(pool, labels, max(1, params["n_drafts"])) if pool else []
    drafts = []
    for subset in groups:
        ranked = rerank_ranks(subset)
        with deps.stage("context"):
            context = format_context(ranked, request.max_context_chars)
        with deps.stage("generation"):
            text = deps.ask("answer", query=question, context=context.text).strip()
        with deps.stage("control"):
            score = parse_score(deps.ask("confidence", query=question, answer=text, context=context.text))
        drafts.append({"chunks": ranked, "context": context, "text": text, "score": score})
    if not drafts:
        with deps.stage("generation"):
            text = deps.ask("answer", query=question, context="").strip()
        return finish(SPEC, deps, Answer(text=text, raw_response=text, model=deps.llm_model), [],
                      format_context([], request.max_context_chars), {"drafts": []}, warnings)
    best = max(enumerate(drafts), key=lambda item: (item[1]["score"], -item[0]))[1]
    used = {c.chunk.id for c in best["chunks"]}
    chunks = rerank_ranks([*best["chunks"], *[c for c in pool if c.chunk.id not in used]][:k])
    return finish(SPEC, deps, Answer(text=best["text"], raw_response=best["text"], model=deps.llm_model), chunks,
                  best["context"],
                  {"candidates": len(pool), "clusters": int(len(set(labels.tolist()))),
                   "drafts": [{"chunks": [c.chunk.id for c in d["chunks"]], "score": round(d["score"], 3),
                               "chosen": d is best} for d in drafts]}, warnings)
