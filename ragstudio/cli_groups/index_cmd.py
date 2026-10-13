"""`ragstudio index ...`: build, inspect, search and delete indices."""
from __future__ import annotations

import argparse
from typing import Any

from ..config.loader import load
from ..core.errors import LeakageError
from ..db.repository import Repo
from ..experiments import index_builder
from ..processing.chunking import STRATEGIES
from ..providers.routing import embed, resolve_endpoint
from ..retrieval import MODES, retrieve
from ..stores import KINDS
from .common import command, json_value, progress_printer


def _build(args: argparse.Namespace) -> Any:
    cfg = load()
    with Repo() as repo:
        corpus = repo.get_corpus(args.corpus)
        only = None
        if args.split:
            splits = repo.get_splits(corpus["id"])
            if args.split not in splits:
                raise LeakageError(f"corpus '{corpus['name']}' has no '{args.split}' split")
            only = splits[args.split]
        documents = repo.corpus_documents(corpus["id"], only)
        chunking = json_value(args.chunking, "--chunking") or {}
        for key in ("strategy", "size", "overlap"):
            if getattr(args, key) is not None:
                chunking[key] = getattr(args, key)
        embedder = resolve_endpoint("embedding", args.embedding_model, cfg)
        llm = resolve_endpoint("llm", args.llm, cfg) if args.enrich else None
        store, reused = index_builder.build_index(
            documents, corpus_id=corpus["id"], chunking=chunking, embedder=embedder, store=args.store,
            split=args.split, enrich=args.enrich, llm=llm, language=args.language or corpus["language"] or "pt",
            batch_size=cfg.get_int("embedding", "batch_size", 32), force=args.force,
            progress=progress_printer(args.stream))
        repo.register_index(store.meta.to_dict(), str(store.path))
    return {**store.meta.to_dict(), "reused": reused, "path": str(store.path)}


def _list(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        corpus_id = repo.get_corpus(args.corpus)["id"] if args.corpus else None
        return [{k: i[k] for k in ("index_hash", "corpus_id", "split", "chunking", "embedding_model", "store",
                                   "enrich", "dim", "chunks", "documents", "created_at")}
                for i in repo.list_indices(corpus_id)]


def _describe(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return repo.get_index(args.index)


def _delete(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        row = repo.get_index(args.index)
        repo.delete_index(row["index_hash"])
    index_builder.delete_index(row["index_hash"])
    return {"deleted": row["index_hash"]}


def _search(args: argparse.Namespace) -> Any:
    cfg = load()
    with Repo() as repo:
        row = repo.get_index(args.index)
    store = index_builder.load_index(row["index_hash"])
    embedder = resolve_endpoint("embedding", row["embedding_model"] if cfg.provider() != "mock" else None, cfg)
    hits = retrieve(store, lambda q: embed(embedder, [q]).vectors[0], args.query, args.k, mode=args.mode,
                    filters=json_value(args.filters, "--filters"))
    return [{"rank": h.rank, "score": round(h.score, 6), "source": h.source, "chunk_id": h.chunk.id,
             "char_start": h.chunk.char_start, "char_end": h.chunk.char_end,
             "text": h.chunk.text[:args.preview]} for h in hits]


def register(groups: Any) -> None:
    sub = groups.add_parser("index", help="chunking + embeddings + stores").add_subparsers(dest="command",
                                                                                           required=True)
    p = command(sub, "build", _build, "build (or reuse) the index for a corpus x chunking x embedding model")
    p.add_argument("--corpus", required=True)
    p.add_argument("--chunking", help='JSON such as {"strategy":"fixed","size":1000,"overlap":150} or @file')
    p.add_argument("--strategy", choices=tuple(STRATEGIES))
    p.add_argument("--size", type=int)
    p.add_argument("--overlap", type=int)
    p.add_argument("--embedding-model")
    p.add_argument("--store", choices=KINDS, default="memory")
    p.add_argument("--split", choices=("train", "validation", "test"))
    p.add_argument("--enrich", choices=("contextual",))
    p.add_argument("--llm", help="model used by --enrich")
    p.add_argument("--language")
    p.add_argument("--force", action="store_true", help="rebuild even if the index exists")
    p.add_argument("--stream", action="store_true")
    command(sub, "list", _list, "indices in the database").add_argument("--corpus")
    command(sub, "describe", _describe, "index metadata and chunk statistics").add_argument("--index", required=True)
    command(sub, "delete", _delete, "delete an index not used by completed runs").add_argument("--index",
                                                                                              required=True)
    p = command(sub, "search", _search, "query an index directly (no generation)")
    p.add_argument("--index", required=True, help="index hash or unique prefix")
    p.add_argument("--query", required=True)
    p.add_argument("--mode", choices=MODES, default="dense")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--filters", help='JSON such as {"document_id": ["doc-a"]}')
    p.add_argument("--preview", type=int, default=200)
