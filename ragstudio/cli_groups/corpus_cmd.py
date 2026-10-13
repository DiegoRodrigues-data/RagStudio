"""`ragstudio corpus ...`: import documents, inspect their profile, define train/validation/test splits."""
from __future__ import annotations

import argparse
from typing import Any

from ..core.errors import ValidationError
from ..db.repository import Repo
from ..ingest.cleaner import FLAGS
from ..ingest.loaders import load_path
from ..ingest.profile import corpus_profile
from ..ingest.splits import assert_disjoint, make_splits, splits_hash
from ..processing.normalize import prepare
from .common import command, csv_list, json_value, progress_printer, warn


def _import(args: argparse.Namespace) -> Any:
    flags = list(FLAGS) if args.clean == "all" else csv_list(args.clean)
    with Repo() as repo:  # fail before a long PDF conversion, not after it
        if any(c["name"] == args.name for c in repo.list_corpora()):
            raise ValidationError(f"corpus '{args.name}' already exists")
    documents, warnings = load_path(args.path, args.format, progress_printer(args.stream))
    for message in warnings:
        warn(message)
    prepared = [prepare(doc, flags or None, args.language) for doc in documents]
    profile = corpus_profile([p for _, p in prepared])
    with Repo() as repo:
        corpus = repo.create_corpus(args.name, prepared, profile, args.description or "", str(args.path), flags)
    return {"id": corpus["id"], "name": corpus["name"], "documents": len(prepared), "skipped": len(warnings),
            "profile": profile, "cleaning": flags}


def _list(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return [{"id": c["id"], "name": c["name"], "documents": c["documents"], "language": c["language"],
                 "total_chars": c["profile"].get("total_chars"), "created_at": c["created_at"]}
                for c in repo.list_corpora()]


def _describe(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        corpus = repo.get_corpus(args.name)
        splits = repo.get_splits(corpus["id"])
        return {**corpus, "splits": {k: len(v) for k, v in splits.items()}, "split_documents": splits,
                "indices": [i["index_hash"] for i in repo.list_indices(corpus["id"])],
                "documents": [{"doc_id": d["doc_id"], "chars": d["chars"], "format": d["format"],
                               "language": d["language"], "sha256": d["sha256"]}
                              for d in repo.document_rows(corpus["id"])]}


def _profile(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        corpus = repo.get_corpus(args.name)
        return {"corpus": corpus["profile"],
                "documents": [{"doc_id": d["doc_id"], **d["profile"]} for d in repo.document_rows(corpus["id"])]}


def _document(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        corpus = repo.get_corpus(args.name)
        row = repo.get_document(corpus["id"], args.doc_id)
    return {"corpus": corpus["name"], **row}


def _split(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        corpus = repo.get_corpus(args.name)
        rows = repo.document_rows(corpus["id"])
        ids = [r["doc_id"] for r in rows]
        if args.assign:
            splits = {k: sorted(v) for k, v in (json_value(args.assign, "--assign") or {}).items()}
            unknown = sorted({d for v in splits.values() for d in v} - set(ids))
            if unknown:
                raise ValidationError(f"unknown document ids in --assign: {unknown}")
        else:
            ratios = {"train": args.train, "validation": args.validation, "test": args.test}
            strata = {r["doc_id"]: r["metadata"].get(args.stratify_by) for r in rows} if args.stratify_by else None
            splits = make_splits(ids, ratios, args.seed, strata)
        assert_disjoint(splits)
        digest = splits_hash(splits)
        repo.set_splits(corpus["id"], splits, digest, args.seed)
    return {"corpus": corpus["name"], "splits": splits, "split_hash": digest, "seed": args.seed}


def _delete(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        corpus = repo.get_corpus(args.name)
        if args.confirm != corpus["name"]:
            raise ValidationError(f"pass --confirm \"{corpus['name']}\" to delete this corpus")
        repo.delete_corpus(corpus["id"])
    return {"deleted": corpus["name"]}


def register(groups: Any) -> None:
    sub = groups.add_parser("corpus", help="documents and corpus characteristics").add_subparsers(dest="command",
                                                                                                  required=True)
    p = command(sub, "import", _import, "load a file or folder (.md .txt .json .jsonl .pdf) as a named corpus")
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--format", help="force a loader (md, txt, json, jsonl, pdf)")
    p.add_argument("--language", help="override the detected language (pt, en)")
    p.add_argument("--clean", default="", help=f"'all' or comma separated flags: {', '.join(FLAGS)}")
    p.add_argument("--description")
    p.add_argument("--stream", action="store_true", help="print one progress line per file (PDF conversion is slow)")
    command(sub, "list", _list, "corpora in the database")
    command(sub, "describe", _describe, "corpus, documents, splits and indices").add_argument("--name", required=True)
    command(sub, "profile", _profile, "characteristics of the corpus and of each document").add_argument(
        "--name", required=True)
    p = command(sub, "document", _document, "one document: normalized text, metadata and profile")
    p.add_argument("--name", required=True)
    p.add_argument("--doc-id", required=True)
    p = command(sub, "split", _split, "define train/validation/test splits (ratios or explicit assignment)")
    p.add_argument("--name", required=True)
    p.add_argument("--train", type=float, default=0.0)
    p.add_argument("--validation", type=float, default=0.0)
    p.add_argument("--test", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--stratify-by", help="document metadata key")
    p.add_argument("--assign", help='explicit JSON {"train": [...], "test": [...]} or @file')
    p = command(sub, "delete", _delete, "delete a corpus that has no indices")
    p.add_argument("--name", required=True)
    p.add_argument("--confirm", required=True)
