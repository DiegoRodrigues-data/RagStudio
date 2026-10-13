"""JSON / JSONL corpus loader: a list of {"id", "text", ...metadata} records already in text form."""
from __future__ import annotations

import json
from pathlib import Path

from ...core.errors import ValidationError
from ...core.models import Document
from .markdown import read_text


def load(path: Path) -> list[Document]:
    from . import make_document, slugify
    raw = read_text(path)
    try:
        if path.suffix.lower() == ".jsonl":
            records = [json.loads(line) for line in raw.splitlines() if line.strip()]
        else:
            data = json.loads(raw)
            records = data.get("documents", []) if isinstance(data, dict) else data
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON ({exc})") from exc
    if not isinstance(records, list) or not records:
        raise ValidationError(f"{path}: expected a non-empty list of documents")
    documents = []
    for n, record in enumerate(records, 1):
        if not isinstance(record, dict) or not str(record.get("text", "")).strip():
            raise ValidationError(f"{path}: record {n} has no 'text'")
        meta = {k: v for k, v in record.items() if k not in ("id", "text")}
        doc_id = slugify(str(record.get("id") or f"{path.stem}-{n}"))
        documents.append(make_document(doc_id, str(record["text"]), f"{path}#{n}", "json", metadata=meta))
    return documents
