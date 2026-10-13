"""Plain-text loader."""
from __future__ import annotations

from pathlib import Path

from ...core.models import Document
from .markdown import read_text


def load(path: Path) -> list[Document]:
    from . import make_document, slugify
    return [make_document(slugify(path.stem), read_text(path), str(path), "text")]
