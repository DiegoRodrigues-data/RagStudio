"""Contextual compression: an LLM keeps only the sentences of each chunk that help answer the question.

Ported from `ragkit.rag_context_compression`.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.pipeline import finish, generate, pool_size, select

SPEC = TechniqueSpec(
    name="context_compression", title="Contextual Compression", stage="post_retrieval", version="1.0.0", family="context",
    description="Retrieve, then compress each chunk to its question-relevant sentences before answering.",
    params={"max_chunk_chars": Param(5000, "characters of each chunk sent to the compressor"),
            "drop_empty": Param(True, "drop chunks the compressor found irrelevant")},
    reference="https://arxiv.org/abs/2410.12837", origin="ragkit.rag_context_compression", status="implemented",
)


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    warnings: list[str] = []
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters)
    selected = select(deps, question, pool, request.k)
    compressed, ratios = [], []
    with deps.stage("compression"):
        for item in selected:
            original = item.chunk.text
            snippet = deps.ask("extract_essential", query=question, text=original[:params["max_chunk_chars"]]).strip()
            ratios.append({"chunk_id": item.chunk.id, "original_chars": len(original),
                           "compressed_chars": len(snippet),
                           "ratio": round(len(snippet) / len(original), 4) if original else 0.0})
            if snippet:
                compressed.append(item.with_text(snippet, compressed=True, original_chars=len(original)))
            elif not params["drop_empty"]:
                compressed.append(item)
    if not compressed and selected:
        warnings.append("compressor returned nothing for every chunk; original chunks were kept")
        compressed = selected
    chunks = [c.with_rank(i) for i, c in enumerate(compressed, 1)]
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    before, after = sum(r["original_chars"] for r in ratios), sum(r["compressed_chars"] for r in ratios)
    return finish(SPEC, deps, answer, chunks, context,
                  {"chunks_before": len(selected), "chunks_after": len(chunks), "chars_before": before,
                   "chars_after": after, "compression_ratio": round(after / before, 4) if before else 0.0,
                   "per_chunk": ratios}, warnings)
