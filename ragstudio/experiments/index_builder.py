"""Builds or reuses an index. The index hash covers everything that changes the vectors, so two techniques asking
for the same (documents, chunking, embedding model, enrichment, store) share one index and one embedding bill."""
from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core import paths
from ..core.errors import NotFoundError, ValidationError
from ..core.hashing import sha256_json
from ..core.models import Chunk, Document
from ..ingest.profile import chunking_profile
from ..processing.chunking import chunk_document, normalize_config
from ..prompts import PromptSet
from ..providers import routing
from ..providers.base import Endpoint
from ..providers.cache import EmbeddingCache
from ..stores import IndexMeta, MemoryStore, create
from ..stores import load as load_store

ENRICHMENTS = (None, "contextual")
Progress = Callable[[dict[str, Any]], None]


def compute_index_hash(documents: list[Document], chunking: dict[str, Any], embedder: Endpoint, store: str = "memory",
                       split: str | None = None, enrich: str | None = None, enrich_model: str = "",
                       language: str = "") -> str:
    return sha256_json({
        "documents": sorted((d.id, d.sha256) for d in documents), "chunking": normalize_config(chunking),
        "embedding": [embedder.provider, embedder.model], "store": store, "split": split, "enrich": enrich,
        "enrich_model": enrich_model if enrich else "", "enrich_language": language if enrich else "",
    })


def index_path(index_hash: str) -> Path:
    return paths.indices_dir() / index_hash


def load_index(index_hash: str) -> MemoryStore:
    matches = [p for p in paths.indices_dir().iterdir() if p.is_dir() and p.name.startswith(index_hash)]
    if len(matches) != 1:
        raise NotFoundError(f"index '{index_hash}' not found" if not matches else f"'{index_hash}' is ambiguous")
    return load_store(matches[0])


def delete_index(index_hash: str) -> str:
    store = load_index(index_hash)
    assert store.path is not None
    shutil.rmtree(store.path)
    return store.meta.index_hash


def build_index(documents: list[Document], *, corpus_id: str, chunking: dict[str, Any] | None, embedder: Endpoint,
                store: str = "memory", split: str | None = None, enrich: str | None = None,
                llm: Endpoint | None = None, language: str = "pt", batch_size: int = 32, timeout: int = 60,
                use_cache: bool = True, force: bool = False,
                progress: Progress | None = None) -> tuple[MemoryStore, bool]:
    """Returns (store, reused). `enrich="contextual"` prefixes each chunk with an LLM-written sentence situating it
    in its document before embedding and lexical indexing (the chunk text and offsets stay untouched)."""
    if enrich not in ENRICHMENTS:
        raise ValidationError(f"unknown enrichment '{enrich}' (available: {ENRICHMENTS})")
    if enrich and llm is None:
        raise ValidationError("contextual enrichment needs an LLM endpoint")
    if not documents:
        raise ValidationError("cannot build an index without documents")
    cfg = normalize_config(chunking)
    digest = compute_index_hash(documents, cfg, embedder, store, split, enrich, llm.model if llm else "", language)
    target = index_path(digest)
    if target.is_dir() and not force:
        return load_store(target), True
    emit = progress or (lambda event: None)

    build_usage: dict[str, Any] = {"embedding_tokens": 0, "embedding_cache_hits": 0, "llm_calls": 0,
                                   "prompt_tokens": 0, "completion_tokens": 0, "chunking_embedding_tokens": 0}
    chunk_cache = EmbeddingCache() if use_cache else None

    def embed_for_chunking(texts: list[str]) -> list[list[float]]:
        """Semantic chunking embeds sentences to find its boundaries; that cost belongs to the index build."""
        result = routing.embed(embedder, texts, batch_size=batch_size, timeout=timeout, cache=chunk_cache)
        build_usage["chunking_embedding_tokens"] += result.tokens
        return result.vectors

    chunks: list[Chunk] = []
    try:
        for doc in documents:
            chunks.extend(chunk_document(doc, cfg, embed_for_chunking))
    finally:
        if chunk_cache:
            chunk_cache.close()
    if not chunks:
        raise ValidationError("chunking produced no chunks")
    emit({"event": "chunked", "chunks": len(chunks), "documents": len(documents)})

    index_texts = [c.text for c in chunks]
    if enrich == "contextual":
        assert llm is not None
        chunks, index_texts = _contextualize(documents, chunks, llm, language, build_usage, emit)

    cache = EmbeddingCache() if use_cache else None
    vectors: list[list[float]] = []
    try:
        for offset in range(0, len(index_texts), batch_size):
            result = routing.embed(embedder, index_texts[offset:offset + batch_size], batch_size=batch_size,
                                   timeout=timeout, cache=cache)
            vectors.extend(result.vectors)
            build_usage["embedding_tokens"] += result.tokens
            build_usage["embedding_cache_hits"] += result.cache_hits
            emit({"event": "embedded", "done": len(vectors), "total": len(index_texts)})
    finally:
        if cache:
            cache.close()

    meta = IndexMeta(index_hash=digest, corpus_id=corpus_id, chunking=cfg, embedding_model=embedder.model,
                     embedding_provider=embedder.provider, store=store, split=split, enrich=enrich,
                     created_at=datetime.now(UTC).isoformat(timespec="seconds"),
                     chunking_profile=chunking_profile([len(c.text) for c in chunks]), build_usage=build_usage)
    built = create(store, meta)
    built.add_documents([{"id": d.id, "text": d.text, "chars": d.chars, "language": d.language, "format": d.format,
                          "metadata": d.metadata} for d in documents])
    built.add(chunks, vectors, index_texts)
    if target.is_dir():
        shutil.rmtree(target)
    built.persist(target)
    emit({"event": "persisted", "index_hash": digest, "path": str(target)})
    return built, False


def _contextualize(documents: list[Document], chunks: list[Chunk], llm: Endpoint, language: str,
                   usage: dict[str, Any], emit: Progress) -> tuple[list[Chunk], list[str]]:
    prompts = PromptSet(language)
    by_id = {d.id: d for d in documents}
    out: list[Chunk] = []
    texts: list[str] = []
    for n, chunk in enumerate(chunks, 1):
        doc = by_id[chunk.document_id]
        variables = {"document": doc.text[:4000], "chunk": chunk.text}
        prompt = prompts.render("context_prefix", **variables)
        result = routing.chat(llm, prompt.messages(), max_tokens=120, task="context_prefix", inputs=variables)
        prefix = result.text.strip()
        usage["llm_calls"] += 1
        usage["prompt_tokens"] += result.prompt_tokens
        usage["completion_tokens"] += result.completion_tokens
        out.append(Chunk(chunk.id, chunk.document_id, chunk.index, chunk.text, chunk.char_start, chunk.char_end,
                         chunk.parent_id, {**chunk.metadata, "context_prefix": prefix}))
        texts.append(f"{prefix}\n{chunk.text}" if prefix else chunk.text)
        if n % 20 == 0 or n == len(chunks):
            emit({"event": "enriched", "done": n, "total": len(chunks)})
    return out, texts
