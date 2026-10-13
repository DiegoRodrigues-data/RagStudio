"""Parent-child (small-to-big) retrieval: search small child chunks, answer from their larger parents.

Needs an index built with `chunking.strategy = parent_child`; with any other chunking the technique degrades to
naive retrieval and says so in `warnings`.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import Chunk, RetrievedChunk
from ..core.pipeline import finish, generate, rerank_ranks

SPEC = TechniqueSpec(
    name="parent_child", title="Parent-Child Retrieval", stage="post_retrieval", ignores=("reranker",), version="1.0.0", family="structure",
    description="Retrieve child chunks and send their (deduplicated) parent spans to the model.",
    params={"children_factor": Param(3, "child chunks retrieved per final parent")},
    requires=("embedder", "llm", "index:parent_child"),
    reference="https://arxiv.org/abs/2410.12837", origin="new", status="implemented",
)


def to_parents(children: list[RetrievedChunk], deps: TechniqueDeps, k: int) -> tuple[list[RetrievedChunk], int]:
    """Best-scoring child decides each parent's score; returns (parents, children without parent metadata)."""
    parents: dict[tuple[str, int, int], RetrievedChunk] = {}
    orphans = 0
    for child in children:
        meta = child.chunk.metadata
        if "parent_start" not in meta:
            orphans += 1
            parents.setdefault((child.chunk.document_id, child.chunk.char_start, child.chunk.char_end), child)
            continue
        start, end = int(meta["parent_start"]), int(meta["parent_end"])
        key = (child.chunk.document_id, start, end)
        if key in parents:
            continue
        text = deps.store.document_text(child.chunk.document_id)[start:end].strip()
        parent = Chunk(id=child.chunk.parent_id or f"{child.chunk.document_id}:p{start}",
                       document_id=child.chunk.document_id, index=int(meta.get("parent", 0)), text=text,
                       char_start=start, char_end=end, metadata={"matched_child": child.chunk.id})
        parents[key] = RetrievedChunk(parent, child.score, child.rank, f"{child.source}+parent")
    ordered = sorted(parents.values(), key=lambda c: (-c.score, c.chunk.id))[:k]
    return rerank_ranks(ordered), orphans


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("retrieval"):
        children = deps.retrieve(question, request.k * max(1, params["children_factor"]), filters=request.filters)
        chunks, orphans = to_parents(children, deps, request.k)
    warnings = []
    if orphans:
        warnings.append(f"{orphans} of {len(children)} retrieved chunks have no parent span: build the index with "
                        "chunking.strategy=parent_child (behaving like naive for those chunks)")
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"children_retrieved": len(children), "parents": len(chunks), "orphans": orphans}, warnings)
