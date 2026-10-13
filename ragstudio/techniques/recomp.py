"""RECOMP (prototype): compress what was retrieved into a short text before the model reads it.

Reference: Xu, Shi & Choi, "RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation"
(ICLR 2024).

Two compressors, as in the paper:
- `compressor="abstractive"`: ONE query-focused summary of all retrieved passages replaces them in the context;
- `compressor="extractive"`: the `n_sentences` sentences most similar to the question are kept, by embedding, with
  no LLM call for compression.

Selective augmentation: when the abstractive compressor judges that nothing retrieved helps, it returns nothing and
the model answers without context (`selective`). With `selective=false` the uncompressed passages are used instead.

Prototype scope, stated plainly: the paper TRAINS both compressors (a dual encoder for sentences and a summarizer
distilled from a large model); here the summary is a prompt to the run's LLM and the sentence ranking uses the run's
embedding model. It differs from `context_compression`, which calls the LLM once per chunk and keeps each chunk
separate. The retrieved chunks stay in the result, so retrieval metrics still describe what was retrieved, while
`context_coverage` describes what survived the compression.
"""
from __future__ import annotations

from ..core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec
from ..core.models import Answer, Context
from ..core.pipeline import finish, format_context, generate, pool_size, rerank_ranks, select, synthetic_chunk
from ..core.text import split_sentences
from . import _vectors

SPEC = TechniqueSpec(
    name="recomp", title="RECOMP", stage="post_retrieval", version="0.1.0", family="context",
    description="Compress the retrieved passages into one query-focused summary, or into their most relevant "
                "sentences, before answering.",
    params={"compressor": Param("abstractive", "abstractive: one LLM summary; extractive: top sentences by embedding",
                                ("abstractive", "extractive")),
            "selective": Param(True, "answer without context when the summary finds nothing useful"),
            "n_sentences": Param(5, "sentences kept by the extractive compressor"),
            "passage_chars": Param(1500, "characters of each passage sent to the summarizer")},
    reference="https://arxiv.org/abs/2310.04408", origin="new", status="prototype",
)
WARNING = "recomp prompts the run's LLM and embedder instead of trained compressors (see module docstring)"


def top_sentences(deps: TechniqueDeps, question: str, texts: list[str], limit: int) -> list[set[str]]:
    """For each text, the sentences that are among the `limit` most similar to the question overall."""
    sentences = [(position, s) for position, text in enumerate(texts) for s in split_sentences(text) if len(s) > 20]
    if not sentences:
        return [set() for _ in texts]
    vectors = deps.embed([question] + [s for _, s in sentences])
    scores = _vectors.similarities(_vectors.unit_rows(vectors[1:]), vectors[0])
    order = sorted(range(len(sentences)), key=lambda i: (-float(scores[i]), i))[:limit]
    kept: list[set[str]] = [set() for _ in texts]
    for i in order:
        kept[sentences[i][0]].add(sentences[i][1])
    return kept


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question = request.query.text
    warnings = [WARNING]
    with deps.stage("retrieval"):
        pool = deps.retrieve(question, pool_size(deps, request.k), filters=request.filters)
    retrieved = select(deps, question, pool, request.k)
    before = sum(len(c.chunk.text) for c in retrieved)
    diagnostics = {"compressor": params["compressor"], "chunks_before": len(retrieved), "chars_before": before}
    if params["compressor"] == "extractive":
        with deps.stage("compression"):
            kept = top_sentences(deps, question, [c.chunk.text for c in retrieved], max(1, params["n_sentences"]))
            compressed = [item.with_text(" ".join(s for s in split_sentences(item.chunk.text) if s in chosen),
                                         compressed=True, original_chars=len(item.chunk.text))
                          for item, chosen in zip(retrieved, kept, strict=True) if chosen]
        chunks = rerank_ranks(compressed or retrieved)
        answer, context = generate(deps, question, chunks, request.max_context_chars)
        after = sum(len(c.chunk.text) for c in chunks)
        return finish(SPEC, deps, answer, chunks, context,
                      {**diagnostics, "chunks_after": len(chunks), "chars_after": after,
                       "compression_ratio": round(after / before, 4) if before else 0.0}, warnings)
    with deps.stage("compression"):
        raw = deps.ask("recomp_summary", query=question,
                       passages=[c.chunk.text[:params["passage_chars"]] for c in retrieved]).strip() if retrieved else ""
    summary = "" if raw.upper().strip(". ") in ("", "NONE") else raw
    diagnostics.update({"chars_after": len(summary), "compression_ratio": round(len(summary) / before, 4) if before
                        else 0.0, "summary_empty": not summary})
    if not summary and not params["selective"]:
        warnings.append("the summary found nothing useful; the uncompressed passages were used")
        answer, context = generate(deps, question, retrieved, request.max_context_chars)
        return finish(SPEC, deps, answer, retrieved, context, diagnostics, warnings)
    if not summary:  # selective augmentation: nothing worth prepending
        with deps.stage("generation"):
            text = deps.ask("answer_direct", query=question)
        return finish(SPEC, deps, Answer(text=text.strip(), raw_response=text, model=deps.llm_model), retrieved,
                      Context("", (), 0, False), {**diagnostics, "answered_without_context": True}, warnings)
    passage = synthetic_chunk("recomp:summary", retrieved[0].chunk.document_id, summary, 0.0, len(retrieved) + 1,
                              "recomp:summary", sources=[c.chunk.id for c in retrieved])
    with deps.stage("context"):
        context = format_context([passage.with_rank(1)], request.max_context_chars)
    with deps.stage("generation"):
        text = deps.ask("answer", query=question, context=context.text)
    return finish(SPEC, deps, Answer(text=text.strip(), raw_response=text, model=deps.llm_model),
                  [*retrieved, passage], context, diagnostics, warnings, cited=[passage])


