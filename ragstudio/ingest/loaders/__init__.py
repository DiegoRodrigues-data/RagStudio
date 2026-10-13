"""Document loading: file or directory -> validated, normalized `Document` records."""
from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from ...core.errors import ValidationError
from ...core.hashing import sha256_text
from ...core.models import Document
from . import json_corpus, markdown, pdf_docling, text

MAX_CHARS = 20_000_000
LOADERS: dict[str, Callable[[Path], list[Document]]] = {
    ".md": markdown.load, ".markdown": markdown.load, ".txt": text.load, ".pdf": pdf_docling.load,
    ".json": json_corpus.load, ".jsonl": json_corpus.load,
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower() or "doc"


def normalize_text(raw: str) -> str:
    """Unix newlines, no BOM, no trailing spaces; offsets used everywhere refer to this normalized text."""
    raw = raw.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in raw.split("\n")).strip() + "\n"


def make_document(doc_id: str, raw: str, source_path: str, fmt: str, pages: int | None = None,
                  metadata: dict | None = None) -> Document:
    body = normalize_text(raw)
    if not body.strip():
        raise ValidationError(f"document '{source_path or doc_id}' is empty")
    if len(body) > MAX_CHARS:
        raise ValidationError(f"document '{source_path or doc_id}' exceeds {MAX_CHARS} characters")
    return Document(id=doc_id, text=body, source_path=source_path, sha256=sha256_text(body), format=fmt,
                    chars=len(body), pages=pages, metadata=dict(metadata or {}))


def _failure_summary(root: Path, files: int, warnings: list[str]) -> str:
    """Why nothing was loaded: the distinct reasons, most frequent first, instead of a generic message."""
    if not files:
        return f"no files found in {root}"
    reasons: dict[str, int] = {}
    for warning in warnings:
        reason = warning.split(": ", 1)[-1] if ": " in warning else warning
        reasons[reason] = reasons.get(reason, 0) + 1
    top = sorted(reasons.items(), key=lambda kv: -kv[1])[:3]
    detail = "; ".join(f"{count} file(s): {reason}" for reason, count in top)
    return f"none of the {files} file(s) in {root} could be loaded. {detail}"


def load_path(path: str | Path, fmt: str | None = None,
              progress: Callable[[dict], None] | None = None) -> tuple[list[Document], list[str]]:
    """Load one file or every supported file in a directory (sorted). Returns (documents, warnings).

    `progress` receives {"event": "file", "done", "total", "name", "ok"} after each file (PDF conversion is slow)."""
    root = Path(path).expanduser()
    if not root.exists():
        raise ValidationError(f"path not found: {root}")
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file()
                                                 and not p.name.startswith("."))
    documents: list[Document] = []
    warnings: list[str] = []
    seen: dict[str, str] = {}
    for position, file in enumerate(files, 1):
        suffix = f".{fmt.lstrip('.')}" if fmt else file.suffix.lower()
        loader = LOADERS.get(suffix)
        if loader is None:
            if root.is_file():
                raise ValidationError(f"unsupported format '{file.suffix}' (supported: {sorted(LOADERS)})")
            warnings.append(f"{file.name}: unsupported format '{file.suffix}'")
            continue
        if progress:
            progress({"event": "file_started", "done": position - 1, "total": len(files), "name": file.name})
        try:
            loaded = loader(file)
        except ValidationError as exc:
            if root.is_file():
                raise
            message = str(exc)
            warnings.append(message if message.startswith(file.name) else f"{file.name}: {message}")
            if progress:
                progress({"event": "file", "done": position, "total": len(files), "name": file.name, "ok": False})
            continue
        if progress:
            progress({"event": "file", "done": position, "total": len(files), "name": file.name, "ok": True})
        for doc in loaded:
            if doc.id in seen:
                unique = f"{doc.id}-{doc.sha256[:6]}"
                warnings.append(f"duplicate id '{doc.id}' ({doc.source_path}); renamed to '{unique}'")
                doc = Document(**{**doc.__dict__, "id": unique})
            seen[doc.id] = doc.source_path
            documents.append(doc)
    if not documents:
        raise ValidationError(_failure_summary(root, len(files), warnings))
    return documents, warnings
