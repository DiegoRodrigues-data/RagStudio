"""`ragstudio questions ...`: question sets with expected answers and gold passages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..db.repository import Repo
from ..ingest import questions as question_files
from .common import command, json_value, warn


def _anchor(repo: Repo, questions: list[dict[str, Any]], corpus_ref: str | None) -> None:
    if any(q["gold_passages"] for q in questions):
        if not corpus_ref:
            warn("gold passages were imported without --corpus: offsets were not anchored or validated")
            return
        corpus = repo.get_corpus(corpus_ref)
        for message in question_files.anchor_gold(questions, repo.corpus_documents(corpus["id"])):
            warn(message)


def _import(args: argparse.Namespace) -> Any:
    parsed = question_files.parse_file(args.path)
    with Repo() as repo:
        _anchor(repo, parsed["questions"], args.corpus)
        qset = repo.create_question_set(args.set or parsed["name"], parsed["description"], parsed["language"])
        ids = repo.add_questions(qset["id"], parsed["questions"])
    return {"id": qset["id"], "name": qset["name"], "questions": len(ids),
            "with_gold_passages": sum(1 for q in parsed["questions"] if q["gold_passages"]),
            "with_expected_answer": sum(1 for q in parsed["questions"] if q["expected_answer"])}


def _create(args: argparse.Namespace) -> Any:
    raw = {"code": args.code, "text": args.text, "expected_answer": args.expected_answer,
           "answer_type": args.answer_type, "split": args.split,
           "gold_passages": json_value(args.gold_passages, "--gold-passages") or []}
    with Repo() as repo:
        try:
            qset = repo.get_question_set(args.set)
        except Exception:  # noqa: BLE001 - first question of a new set
            qset = repo.create_question_set(args.set)
        position = len(repo.list_questions(qset["id"])) + 1
        question = question_files.parse_question(raw, position)
        _anchor(repo, [question], args.corpus)
        ids = repo.add_questions(qset["id"], [question])
    return {"id": ids[0], "set": qset["name"], "code": question["code"]}


def _update(args: argparse.Namespace) -> Any:
    changes = {"text": args.text, "expected_answer": args.expected_answer, "answer_type": args.answer_type,
               "split": args.split}
    with Repo() as repo:
        before = repo.get_question(args.id)
        if args.gold_passages is not None:
            gold = question_files.parse_question({"text": before["text"],
                                                  "gold_passages": json_value(args.gold_passages)})["gold_passages"]
            probe = [{"code": before["code"], "gold_passages": gold}]
            _anchor(repo, probe, args.corpus)
            changes["gold_passages"] = gold
        after = repo.update_question(args.id, changes)
    return {"id": after["id"], "version": after["version"], "supersedes_id": after["supersedes_id"],
            "new_version_created": after["version"] != before["version"]}


def _archive(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        row = repo.archive_question(args.id)
    return {"id": row["id"], "archived_at": row["archived_at"]}


def _list(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        if not args.set:
            return repo.list_question_sets()
        qset = repo.get_question_set(args.set)
        return {"set": qset, "questions": repo.list_questions(qset["id"], args.include_archived)}


def _export(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        qset = repo.get_question_set(args.set)
        questions = repo.list_questions(qset["id"])
    payload = {"name": qset["name"], "language": qset["language"], "description": qset["description"],
               "questions": [{"code": q["code"], "text": q["text"], "expected_answer": q["expected_answer"],
                              "answer_type": q["answer_type"], "split": q["split"],
                              "gold_passages": q["gold_passages"], "metadata": q["metadata"]} for q in questions]}
    path = Path(args.output).expanduser()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(path), "questions": len(questions)}


def register(groups: Any) -> None:
    sub = groups.add_parser("questions", help="question sets and ground truth").add_subparsers(dest="command",
                                                                                               required=True)
    p = command(sub, "import-json", _import, "import a question-set JSON file")
    p.add_argument("--path", required=True)
    p.add_argument("--set", help="name of the new question set (default: the file's name)")
    p.add_argument("--corpus", help="corpus used to anchor and validate gold passages")
    p = command(sub, "create", _create, "add one question (creates the set when needed)")
    p.add_argument("--set", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--code")
    p.add_argument("--expected-answer")
    p.add_argument("--answer-type", default="extraction", choices=question_files.ANSWER_TYPES)
    p.add_argument("--split", choices=("train", "validation", "test"))
    p.add_argument("--gold-passages", help='JSON list of {"document_id", "text"}')
    p.add_argument("--corpus")
    p = command(sub, "update", _update, "edit a question (creates a new version once a completed run used it)")
    p.add_argument("--id", required=True)
    p.add_argument("--text")
    p.add_argument("--expected-answer")
    p.add_argument("--answer-type", choices=question_files.ANSWER_TYPES)
    p.add_argument("--split", choices=("train", "validation", "test"))
    p.add_argument("--gold-passages")
    p.add_argument("--corpus")
    command(sub, "archive", _archive, "hide a question from future runs (history is kept)").add_argument(
        "--id", required=True)
    p = command(sub, "list", _list, "question sets, or the questions of one set")
    p.add_argument("--set")
    p.add_argument("--include-archived", action="store_true")
    p = command(sub, "export", _export, "write a question set back to JSON")
    p.add_argument("--set", required=True)
    p.add_argument("--output", required=True)
