"""Question-set files: parsing, validation and anchoring of gold passages to document offsets.

Accepted JSON: {"name": ..., "language": ..., "questions": [...]} or a bare list. Each question:
    {"code": "Q1", "text": "...", "expected_answer": "...", "answer_type": "extraction", "split": "test",
     "gold_passages": [{"document_id": "doc", "text": "literal excerpt", "char_start": 10, "char_end": 80}]}
Legacy JudDoc_Ex keys are accepted too: `id` (code), `resposta_esperada` / `gold_answer`, `tipo_resposta`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.errors import ValidationError
from ..core.models import Document
from ..core.text import normalize

ANSWER_TYPES = ("boolean", "extraction", "classification", "reasoning", "summarization")


def parse_file(path: str | Path) -> dict[str, Any]:
    file = Path(path).expanduser()
    if not file.is_file():
        raise ValidationError(f"question file not found: {file}")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{file}: invalid JSON ({exc})") from exc
    meta = data if isinstance(data, dict) else {}
    items = meta.get("questions", []) if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise ValidationError(f"{file}: no questions found")
    return {"name": meta.get("name") or file.stem, "language": meta.get("language") or "",
            "description": meta.get("description") or "", "questions": [parse_question(q, n) for n, q in
                                                                        enumerate(items, 1)]}


def parse_question(raw: dict[str, Any], position: int = 1) -> dict[str, Any]:
    if not isinstance(raw, dict) or not str(raw.get("text") or "").strip():
        raise ValidationError(f"question {position}: 'text' is required")
    answer_type = raw.get("answer_type") or raw.get("tipo_resposta") or "extraction"
    if answer_type not in ANSWER_TYPES:
        raise ValidationError(f"question {position}: answer_type must be one of {ANSWER_TYPES}")
    gold = []
    for item in raw.get("gold_passages") or []:
        if isinstance(item, str):
            raise ValidationError(f"question {position}: gold passages need a document_id and text")
        if not item.get("document_id") or not str(item.get("text") or "").strip():
            raise ValidationError(f"question {position}: each gold passage needs 'document_id' and 'text'")
        gold.append({"document_id": str(item["document_id"]), "text": str(item["text"]),
                     "char_start": item.get("char_start"), "char_end": item.get("char_end"),
                     "source": item.get("source") or "imported"})
    known = {"code", "id", "text", "expected_answer", "resposta_esperada", "gold_answer", "answer_type",
             "tipo_resposta", "split", "gold_passages", "metadata"}
    return {"code": str(raw.get("code") or raw.get("id") or f"Q{position}"), "text": str(raw["text"]).strip(),
            "expected_answer": raw.get("expected_answer") or raw.get("gold_answer") or raw.get("resposta_esperada"),
            "answer_type": answer_type, "split": raw.get("split"), "gold_passages": gold,
            "metadata": {**(raw.get("metadata") or {}), **{k: v for k, v in raw.items() if k not in known}}}


def anchor_gold(questions: list[dict[str, Any]], documents: list[Document]) -> list[str]:
    """Fill `char_start` / `char_end` of gold passages by locating their text in the corpus documents.

    A passage that is not found literally (after whitespace/accent normalization) raises: an unanchored gold would
    silently turn retrieval metrics into noise."""
    by_id = {d.id: d for d in documents}
    warnings: list[str] = []
    for question in questions:
        for gold in question["gold_passages"]:
            doc = by_id.get(gold["document_id"])
            if doc is None:
                raise ValidationError(f"question {question['code']}: gold passage references unknown document "
                                      f"'{gold['document_id']}' (corpus has: {sorted(by_id)[:8]})")
            if gold.get("char_start") is not None and gold.get("char_end") is not None:
                if doc.text[gold["char_start"]:gold["char_end"]].strip() != gold["text"].strip():
                    warnings.append(f"{question['code']}: offsets of a gold passage in '{doc.id}' do not match its "
                                    "text; re-anchored by text")
                else:
                    continue
            start = doc.text.find(gold["text"])
            if start >= 0:
                gold["char_start"], gold["char_end"] = start, start + len(gold["text"])
                continue
            span = _find_normalized(doc.text, gold["text"])
            if span is None:
                raise ValidationError(f"question {question['code']}: gold passage not found literally in document "
                                      f"'{doc.id}': {gold['text'][:80]!r}")
            gold["char_start"], gold["char_end"] = span
            gold["text"] = doc.text[span[0]:span[1]]
    return warnings


def _find_normalized(text: str, needle: str) -> tuple[int, int] | None:
    """Locate `needle` ignoring case, accents and whitespace runs; returns offsets in the original text."""
    target = normalize(needle).replace(" ", "")
    if not target:
        return None
    compact, positions = [], []
    for i, ch in enumerate(text):
        norm = normalize(ch)
        if norm and not norm.isspace():
            for piece in norm:
                compact.append(piece)
                positions.append(i)
    found = "".join(compact).find(target)
    if found < 0:
        return None
    return positions[found], positions[found + len(target) - 1] + 1
