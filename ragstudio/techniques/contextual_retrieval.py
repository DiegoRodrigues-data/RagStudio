"""Contextual retrieval: chunks are indexed together with an LLM-written sentence situating them in the document.

The work happens at indexing time (`enrich: contextual` in the runbook, see `experiments/index_builder.py`); at query
time this is naive retrieval over the enriched index. On a plain index the technique runs but warns that it is
equivalent to `naive`.

Reference: Anthropic, "Introducing Contextual Retrieval" (2024), https://www.anthropic.com/news/contextual-retrieval
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, pool_size, select

SPEC = TechniqueSpec(
    name="contextual_retrieval", title="Contextual RAG", stage="indexing", version="1.0.0", family="structure",
    description="Retrieve over an index whose chunks were prefixed with document-level context before embedding.",
    params={"prefix_in_context": Param(True, "also show the situating sentence to the answering model")},
    requires=("embedder", "llm", "index:contextual"),
    reference="https://www.anthropic.com/news/contextual-retrieval", origin="new", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    warnings = []
    enriched = getattr(deps.store.meta, "enrich", None) == "contextual"
    if not enriched:
        warnings.append("the index was not built with enrich=contextual; this run is equivalent to naive")
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters)
    chunks = select(deps, question, pool, request.k)
    if params["prefix_in_context"]:
        chunks = [c.with_text(f"{c.chunk.metadata['context_prefix']}\n{c.chunk.text}")
                  if c.chunk.metadata.get("context_prefix") else c for c in chunks]
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"index_enriched": enriched, "prefix_in_context": params["prefix_in_context"],
                   "with_prefix": sum(1 for c in chunks if c.chunk.metadata.get("context_prefix"))}, warnings)
