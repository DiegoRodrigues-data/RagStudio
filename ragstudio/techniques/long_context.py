"""Long-Context RAG: retrieval picks the documents, and the model reads them whole instead of isolated chunks.

Related work: Jiang et al., "LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs" (2024);
Li et al., "Retrieval Augmented Generation or Long-Context LLMs? A Comprehensive Study and Hybrid Approach" (2024).

Chunks are retrieved as usual and only decide WHICH documents matter. The context is then built from the full text
of the best documents, up to `context_chars`. A document that does not fit is cut to a window around the chunks
that matched. The technique uses its own context budget and ignores the run's `max_context_chars`: reading long
is the point, and the cost shows in the prompt tokens.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import Chunk, RetrievedChunk
from ..core.pipeline import finish, generate, pool_size, select

SPEC = TechniqueSpec(
    name="long_context", title="Long-Context RAG", stage="post_retrieval", ignores=("max_context_chars",),
    version="1.0.0", family="context",
    description="Retrieve chunks to choose documents, then send those documents whole to the model.",
    params={"max_documents": Param(3, "documents sent to the model"),
            "context_chars": Param(48000, "context budget of this technique, instead of the run's"),
            "min_window_chars": Param(2000, "smallest useful slice of a document that does not fit whole")},
    reference="https://arxiv.org/abs/2406.15319", origin="new",
)


def document_span(text: str, matched: list[RetrievedChunk], room: int) -> tuple[int, int]:
    """The whole document when it fits in `room`; otherwise a window of `room` characters centred on the matches."""
    if len(text) <= room:
        return 0, len(text)
    low = min(c.chunk.char_start for c in matched)
    high = max(c.chunk.char_end for c in matched)
    start = max(0, min(low - max(0, room - (high - low)) // 2, len(text) - room))
    return start, min(len(text), start + room)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters)
    matched = select(deps, question, pool, request.k)
    by_document: dict[str, list[RetrievedChunk]] = {}
    for item in matched:
        by_document.setdefault(item.chunk.document_id, []).append(item)
    room = max(params["context_chars"], 400)
    documents: list[RetrievedChunk] = []
    with deps.stage("context"):
        for document_id, items in list(by_document.items())[:max(1, params["max_documents"])]:
            if documents and room < params["min_window_chars"]:
                break
            text = deps.store.document_text(document_id)
            start, end = document_span(text, items, room - 80)  # 80: the passage header
            chunk = Chunk(id=f"{document_id}:document", document_id=document_id, index=-1, text=text[start:end],
                          char_start=start, char_end=end,
                          metadata={"whole_document": end - start == len(text), "chunks_matched": len(items)})
            documents.append(RetrievedChunk(chunk, max(i.score for i in items), len(documents) + 1,
                                            "long_context:document"))
            room -= (end - start) + 80
    answer, context = generate(deps, question, documents, params["context_chars"])
    return finish(SPEC, deps, answer, documents, context,
                  {"documents": [d.chunk.document_id for d in documents],
                   "whole_documents": sum(1 for d in documents if d.chunk.metadata["whole_document"]),
                   "chunks_matched": len(matched), "context_chars_budget": params["context_chars"]})
