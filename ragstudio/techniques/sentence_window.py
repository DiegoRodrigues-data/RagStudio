"""Sentence-window retrieval: match on a small chunk, answer from that chunk plus its neighbouring sentences.

Works with any chunking; it is most useful with small chunks (`chunking.strategy = sentence`, small size).
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import Chunk, RetrievedChunk
from ..core.pipeline import finish, generate, pool_size, rerank_ranks, select
from ..processing.chunking.sentence import sentence_spans

SPEC = TechniqueSpec(
    name="sentence_window", title="Sentence Window Retrieval", stage="post_retrieval", version="1.0.0", family="structure",
    description="Retrieve small chunks and expand each one with the sentences around it in the source document.",
    params={"window": Param(2, "sentences added before and after the matched chunk")},
    reference="https://arxiv.org/abs/2410.12837", origin="new", status="implemented",
)


def expand(item: RetrievedChunk, text: str, window: int) -> RetrievedChunk:
    spans = sentence_spans(text)
    inside = [i for i, (s, e) in enumerate(spans) if e > item.chunk.char_start and s < item.chunk.char_end]
    if not inside:
        return item
    first, last = max(0, inside[0] - window), min(len(spans) - 1, inside[-1] + window)
    start, end = min(spans[first][0], item.chunk.char_start), max(spans[last][1], item.chunk.char_end)
    chunk = Chunk(id=item.chunk.id, document_id=item.chunk.document_id, index=item.chunk.index,
                  text=text[start:end].strip(), char_start=start, char_end=end, parent_id=item.chunk.parent_id,
                  metadata={**item.chunk.metadata, "matched_start": item.chunk.char_start,
                            "matched_end": item.chunk.char_end})
    return RetrievedChunk(chunk, item.score, item.rank, f"{item.source}+window")


def merge_overlapping(items: list[RetrievedChunk], texts: dict[str, str]) -> list[RetrievedChunk]:
    """Windows of the same document that overlap become one passage (keeps the best score)."""
    merged: list[RetrievedChunk] = []
    for item in sorted(items, key=lambda c: (c.chunk.document_id, c.chunk.char_start)):
        last = merged[-1] if merged else None
        if last and last.chunk.document_id == item.chunk.document_id and item.chunk.char_start <= last.chunk.char_end:
            keep = last if last.score >= item.score else item
            start, end = last.chunk.char_start, max(last.chunk.char_end, item.chunk.char_end)
            chunk = Chunk(keep.chunk.id, keep.chunk.document_id, keep.chunk.index,
                          texts[keep.chunk.document_id][start:end].strip(), start, end, keep.chunk.parent_id,
                          keep.chunk.metadata)
            merged[-1] = RetrievedChunk(chunk, max(last.score, item.score), keep.rank, keep.source)
        else:
            merged.append(item)
    return rerank_ranks(sorted(merged, key=lambda c: (-c.score, c.chunk.id)))


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters)
    matched = select(deps, question, pool, request.k)
    with deps.stage("context"):
        texts = {doc_id: deps.store.document_text(doc_id) for doc_id in {c.chunk.document_id for c in matched}}
        chunks = merge_overlapping([expand(c, texts[c.chunk.document_id], max(0, params["window"]))
                                    for c in matched], texts)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    before, after = sum(len(c.chunk.text) for c in matched), sum(len(c.chunk.text) for c in chunks)
    return finish(SPEC, deps, answer, chunks, context,
                  {"window": params["window"], "matched": len(matched), "passages": len(chunks),
                   "chars_matched": before, "chars_expanded": after})
