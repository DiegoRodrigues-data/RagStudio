"""Hierarchical Retrieval: choose the documents first, then search for chunks only inside them.

Related work: Liu et al., "Dense Hierarchical Retrieval for Open-Domain Question Answering" (2021).

Stage 1 ranks DOCUMENTS against the question. Each document is represented by the embedding of an LLM summary
(`document_vector="summary"`, one call per document, once per index) or by the mean of its chunk embeddings
(`document_vector="mean"`, no LLM call). Stage 2 is the run's ordinary retrieval, restricted to the chunks of the
`top_documents` best documents. It helps when many documents share vocabulary and chunks from the wrong document
crowd out the right one.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.hashing import sha256_text
from ..core.pipeline import finish, generate, pool_size, select
from . import _vectors

SPEC = TechniqueSpec(
    name="hierarchical", title="Hierarchical Retrieval", stage="retrieval", version="1.0.0", family="structure",
    description="Rank documents by a document-level vector, then retrieve chunks only inside the best documents.",
    params={"top_documents": Param(3, "documents kept by the first stage"),
            "document_vector": Param("summary", "summary: embedding of an LLM summary; mean: mean of chunk vectors",
                                     ("summary", "mean")),
            "summary_input_chars": Param(8000, "characters of each document sent to the summarizer")},
    requires=("embedder", "llm", "index:aux"),
    reference="https://arxiv.org/abs/2110.15439", origin="new",
)


def document_ids(deps: TechniqueDeps) -> list[str]:
    return list(dict.fromkeys(c.document_id for c in deps.store.all_chunks()))


def summary_vectors(deps: TechniqueDeps, ids: list[str], input_chars: int) -> tuple[np.ndarray, bool]:
    key = "docsum_" + sha256_text(f"{deps.llm_model}|{deps.language}|{input_chars}")[:12]
    summaries = deps.store.aux_load(key)
    built_now = summaries is None
    if built_now:
        with deps.stage("index_build"):
            summaries = {doc: deps.ask("summarize", text=deps.store.document_text(doc)[:input_chars]).strip()
                         for doc in ids}
            deps.store.aux_save(key, summaries)
    texts = [summaries.get(doc) or deps.store.document_text(doc)[:500] for doc in ids]
    return _vectors.vectors(deps, key, "documents", texts), built_now


def mean_vectors(deps: TechniqueDeps, ids: list[str]) -> np.ndarray:
    groups: dict[str, list[list[float]]] = {doc: [] for doc in ids}
    for chunk in deps.store.all_chunks():
        groups[chunk.document_id].append(deps.store.embedding(chunk.id))
    return _vectors.unit_rows([np.mean(np.asarray(groups[doc], dtype=np.float64), axis=0).tolist() for doc in ids])


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    ids = document_ids(deps)
    allowed = (request.filters or {}).get("document_id")
    if allowed is not None:
        wanted = set(allowed if isinstance(allowed, (list, tuple, set)) else [allowed])
        ids = [doc for doc in ids if doc in wanted]
    built_now = False
    if params["document_vector"] == "summary":
        matrix, built_now = summary_vectors(deps, ids, params["summary_input_chars"])
    else:
        matrix = mean_vectors(deps, ids)
    with deps.stage("retrieval"):
        vector = deps.embed([question])[0]
        ranked = _vectors.top(_vectors.similarities(matrix, vector), max(1, params["top_documents"]), minimum=-1.0)
        chosen = [ids[i] for i, _ in ranked]
        filters: dict[str, Any] = {**(request.filters or {}), "document_id": chosen}
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=filters)
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"document_vector": params["document_vector"], "documents_in_index": len(ids),
                   "documents": [{"document_id": ids[i], "score": round(score, 4)} for i, score in ranked],
                   "built_now": built_now})
