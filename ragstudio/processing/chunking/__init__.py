"""Chunking strategies. Every strategy returns `Chunk`s whose text is an exact slice of the document text:

    document.text[chunk.char_start:chunk.char_end] == chunk.text

so gold passages anchored by offsets, parent expansion and window expansion all work on the same coordinates.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...core.errors import ValidationError
from ...core.models import Chunk, Document
from . import fixed, markdown_headers, parent_child, recursive, semantic, sentence

STRATEGIES: dict[str, Callable[..., list[tuple[int, int, dict[str, Any]]]]] = {
    "fixed": fixed.spans, "markdown_headers": markdown_headers.spans, "sentence": sentence.spans,
    "parent_child": parent_child.spans, "recursive": recursive.spans, "semantic": semantic.spans,
}
NEEDS_EMBEDDER = ("semantic",)
DEFAULT = {"strategy": "fixed", "size": 1000, "overlap": 150}


def normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """Explicit, ordered configuration (it is part of the index hash)."""
    cfg = {**DEFAULT, **(config or {})}
    if cfg["strategy"] not in STRATEGIES:
        raise ValidationError(f"unknown chunking strategy '{cfg['strategy']}' (available: {sorted(STRATEGIES)})")
    if int(cfg["size"]) < 50:
        raise ValidationError("chunk size must be at least 50 characters")
    if not 0 <= int(cfg["overlap"]) < int(cfg["size"]):
        raise ValidationError("chunk overlap must be >= 0 and smaller than size")
    return dict(sorted(cfg.items()))


def chunk_document(doc: Document, config: dict[str, Any] | None = None,
                   embed: Callable[[list[str]], list[list[float]]] | None = None) -> list[Chunk]:
    """`embed` is only used by the strategies in NEEDS_EMBEDDER (semantic chunking)."""
    cfg = normalize_config(config)
    options = {k: v for k, v in cfg.items() if k != "strategy"}
    if cfg["strategy"] in NEEDS_EMBEDDER:
        options["embed"] = embed
    chunks: list[Chunk] = []
    for start, end, meta in STRATEGIES[cfg["strategy"]](doc.text, **options):
        start, end = _trim(doc.text, start, end)
        if end <= start:
            continue
        index = len(chunks)
        parent = meta.pop("parent", None)
        chunks.append(Chunk(id=f"{doc.id}:{index}", document_id=doc.id, index=index, text=doc.text[start:end],
                            char_start=start, char_end=end,
                            parent_id=f"{doc.id}:p{parent}" if parent is not None else None, metadata=meta))
    return chunks


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end
