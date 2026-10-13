"""Building blocks shared by techniques: pooling, selection, context assembly, answer generation, result packing.

Techniques compose these functions; logic specific to one technique never lives here.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .contract import TechniqueDeps, TechniqueResult, TechniqueSpec
from .models import Answer, Chunk, Context, RetrievedChunk


def rerank_ranks(chunks: Iterable[RetrievedChunk]) -> list[RetrievedChunk]:
    return [c.with_rank(i) for i, c in enumerate(chunks, 1)]


def merge_pool(*lists: Iterable[RetrievedChunk]) -> list[RetrievedChunk]:
    """Union by chunk id keeping the best score, ordered by score (ties broken by chunk id for determinism)."""
    best: dict[str, RetrievedChunk] = {}
    for items in lists:
        for item in items:
            current = best.get(item.chunk.id)
            if current is None or item.score > current.score:
                best[item.chunk.id] = item
    ordered = sorted(best.values(), key=lambda c: (-c.score, c.chunk.id))
    return rerank_ranks(ordered)


def pool_size(deps: TechniqueDeps, k: int, factor: int = 3) -> int:
    """Candidates to fetch: k when nothing reorders them afterwards, k * factor when the run has a reranker."""
    return k * factor if deps.has_reranker else k


def select(deps: TechniqueDeps, query: str, pool: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
    """Final top-k: the run's reranker when configured (timed as `rerank`), otherwise score order."""
    if deps.has_reranker:
        with deps.stage("rerank"):
            return deps.rerank(query, pool, k)
    return rerank_ranks(sorted(pool, key=lambda c: (-c.score, c.chunk.id))[:k])


def format_context(chunks: list[RetrievedChunk], max_chars: int) -> Context:
    """Numbered passages `[n] (document · chunk)`; stops before exceeding `max_chars` and records truncation."""
    parts: list[str] = []
    used: list[str] = []
    total = 0
    truncated = False
    for n, item in enumerate(chunks, 1):
        # synthetic passages (summaries, community reports, graph facts) have no position in the document
        origin = f"chunk {item.chunk.index}" if item.chunk.index >= 0 else item.source
        block = f"[{n}] ({item.chunk.document_id} · {origin})\n{item.chunk.text.strip()}"
        if total + len(block) > max_chars:
            room = max_chars - total
            truncated = True
            if room > 200:  # keep a useful partial passage rather than dropping it entirely
                parts.append(block[:room])
                used.append(item.chunk.id)
                total += room
            break
        parts.append(block)
        used.append(item.chunk.id)
        total += len(block) + 2
    text = "\n\n".join(parts)
    return Context(text=text, chunk_ids=tuple(used), chars=len(text), truncated=truncated)


def citations(chunks: list[RetrievedChunk], context: Context) -> tuple[dict[str, Any], ...]:
    in_context = set(context.chunk_ids)
    return tuple({"n": n, "chunk_id": c.chunk.id, "document_id": c.chunk.document_id, "chunk_index": c.chunk.index,
                  "char_start": c.chunk.char_start, "char_end": c.chunk.char_end, "score": round(float(c.score), 6)}
                 for n, c in enumerate(chunks, 1) if c.chunk.id in in_context)


def generate(deps: TechniqueDeps, question: str, chunks: list[RetrievedChunk],
             max_context_chars: int) -> tuple[Answer, Context]:
    """Assemble the context (stage `context`) and ask for the grounded answer (stage `generation`)."""
    with deps.stage("context"):
        context = format_context(chunks, max_context_chars)
    with deps.stage("generation"):
        text = deps.ask("answer", query=question, context=context.text)
    return Answer(text=text.strip(), raw_response=text, model=deps.llm_model), context


def answer_without_retrieval(deps: TechniqueDeps, question: str) -> tuple[Answer, Context]:
    """The model answers from its own knowledge (task `answer_direct`): no chunks, an empty context."""
    with deps.stage("retrieval"):
        pass  # the stage is recorded with zero time so every result has the same shape
    with deps.stage("generation"):
        text = deps.ask("answer_direct", query=question)
    return Answer(text=text.strip(), raw_response=text, model=deps.llm_model), Context("", (), 0, False)


def interleave(rankings: Iterable[list[RetrievedChunk]], k: int) -> list[RetrievedChunk]:
    """Round-robin over several rankings, without repeats: every ranking contributes its best chunks first."""
    lists = [list(r) for r in rankings]
    out: list[RetrievedChunk] = []
    seen: set[str] = set()
    for position in range(max((len(r) for r in lists), default=0)):
        for ranking in lists:
            if position < len(ranking) and ranking[position].chunk.id not in seen:
                seen.add(ranking[position].chunk.id)
                out.append(ranking[position])
    return rerank_ranks(out[:k])


def finish(spec: TechniqueSpec, deps: TechniqueDeps, answer: Answer, chunks: list[RetrievedChunk], context: Context,
           diagnostics: dict[str, Any] | None = None, warnings: Iterable[str] = (),
           cited: list[RetrievedChunk] | None = None) -> TechniqueResult:
    """`cited` is the list the context was numbered from, when it is not `chunks` itself (a summary of them)."""
    diag = {"technique": spec.name, "version": spec.version, **(diagnostics or {})}
    return TechniqueResult(answer=answer, contexts=tuple(chunks), context=context,
                           citations=citations(chunks if cited is None else cited, context), diagnostics=diag,
                           timings=tuple(deps.timings()), usage=deps.usage(), warnings=tuple(warnings))


def synthetic_chunk(chunk_id: str, document_id: str, text: str, score: float, rank: int, source: str,
                    **metadata: object) -> RetrievedChunk:
    """A passage that is not a slice of a document (summary, community report, graph facts): index -1, no offsets."""
    return RetrievedChunk(Chunk(id=chunk_id, document_id=document_id, index=-1, text=text, char_start=0, char_end=0,
                                metadata=dict(metadata)), float(score), rank, source)


def parse_lines(raw: str, limit: int) -> list[str]:
    """Lines of an LLM list answer without bullets/numbering, deduplicated, at most `limit`."""
    out: list[str] = []
    for line in raw.splitlines():
        clean = line.strip().lstrip("-*•0123456789.) ").strip()
        if clean and clean not in out:
            out.append(clean)
    return out[:limit]
