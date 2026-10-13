"""Corpus preparation step between loading and chunking: optional cleaning + profile + language."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..core.hashing import sha256_text
from ..core.models import Document
from ..ingest.cleaner import clean
from ..ingest.profile import document_profile


def prepare(doc: Document, cleaning_flags: list[str] | None = None,
            language: str | None = None) -> tuple[Document, dict[str, Any]]:
    """Returns the document that will actually be indexed and its profile."""
    text = clean(doc.text, cleaning_flags) if cleaning_flags else doc.text
    doc = replace(doc, text=text, sha256=sha256_text(text), chars=len(text), language=language or doc.language)
    profile = document_profile(doc)
    return replace(doc, language=profile["language"]), profile
