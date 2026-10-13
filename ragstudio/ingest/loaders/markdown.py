"""Markdown loader."""
from __future__ import annotations

from pathlib import Path

from ...core.errors import ValidationError
from ...core.models import Document


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValidationError(f"cannot decode {path}")


def load(path: Path) -> list[Document]:
    from . import make_document, slugify
    return [make_document(slugify(path.stem), read_text(path), str(path), "markdown")]
