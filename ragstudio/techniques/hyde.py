"""HyDE: generate a hypothetical answer document and retrieve with its embedding.

Reference: Gao, Ma, Lin & Callan, "Precise Zero-Shot Dense Retrieval without Relevance Labels", ACL 2023.
Ported from `ragkit.rag_hyde`.
"""
from __future__ import annotations

import numpy as np

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, pool_size, select

SPEC = TechniqueSpec(
    name="hyde", title="HyDE", stage="query", version="1.0.0", family="query",
    description="Retrieve with the embedding of an LLM-written hypothetical document instead of the question.",
    params={"include_query": Param(False, "average the hypothetical document vector with the question vector")},
    reference="https://aclanthology.org/2023.acl-long.99/", origin="ragkit.rag_hyde", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("query_transform"):
        hypothetical = deps.ask("hypo_doc", query=question).strip() or question
        vectors = deps.embed([hypothetical, question] if params["include_query"] else [hypothetical])
        vector = np.mean(np.asarray(vectors, dtype=float), axis=0).tolist()
    with deps.stage("retrieval"):
        # the hypothetical text is also the lexical query, so bm25/hybrid/rrf runs benefit from it too
        pool = deps.retrieve(hypothetical, pool_size(deps, request.k), query_vector=vector, filters=request.filters)
    chunks = select(deps, question, pool, request.k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"hypothetical_document": hypothetical, "hypothetical_chars": len(hypothetical),
                   "include_query": params["include_query"]})
