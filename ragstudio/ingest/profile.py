"""Document and corpus characteristics: the independent variables of the empirical analysis.

Everything is computed from the normalized text at import time and stored with the document, so results can later
be crossed with size, structure and language (`analysis/characteristics.py`).
"""
from __future__ import annotations

import re
import statistics
from typing import Any

from ..core.models import Document
from ..core.text import tokenize

_PT = frozenset("de que não para com uma os no se na por mais as dos como mas foi ao ele das tem à seu sua ou ser "
                "quando muito há nos já está eu também só pelo pela até isso ela entre era depois sem mesmo aos "
                "ter seus quem nas me esse eles estão você".split())
_EN = frozenset("the of and to in is that it was for on are as with his they at be this from have or by not but "
                "what all were when we there can an your which their said if will each about how up out them "
                "then she many some so these would".split())


def detect_language(text: str) -> str:
    """Stopword vote between pt and en; 'und' when the text is too short or tied."""
    tokens = tokenize(text[:20000])
    pt, en = sum(t in _PT for t in tokens), sum(t in _EN for t in tokens)
    if max(pt, en) < 5 or pt == en:
        return "und"
    return "pt" if pt > en else "en"


def document_profile(doc: Document) -> dict[str, Any]:
    text = doc.text
    lines = text.split("\n")
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    words = tokenize(text)
    table_lines = sum(1 for line in lines if line.strip().startswith("|"))
    list_lines = sum(1 for line in lines if re.match(r"\s*([-*+]|\d+[.)])\s+", line))
    non_empty = sum(1 for line in lines if line.strip()) or 1
    return {
        "chars": len(text), "words": len(words), "lines": len(lines), "paragraphs": len(paragraphs),
        "headings": sum(1 for line in lines if line.startswith("#")),
        "avg_paragraph_chars": round(statistics.fmean(len(p) for p in paragraphs), 1) if paragraphs else 0.0,
        "table_line_ratio": round(table_lines / non_empty, 4), "list_line_ratio": round(list_lines / non_empty, 4),
        "digit_ratio": round(sum(c.isdigit() for c in text) / max(len(text), 1), 4),
        "vocabulary_ratio": round(len(set(words)) / max(len(words), 1), 4),
        "language": doc.language or detect_language(text), "format": doc.format, "pages": doc.pages,
    }


def _summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0, "max": 0, "mean": 0, "median": 0, "stdev": 0}
    return {"min": min(values), "max": max(values), "mean": round(statistics.fmean(values), 2),
            "median": statistics.median(values),
            "stdev": round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0}


def corpus_profile(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    formats: dict[str, int] = {}
    languages: dict[str, int] = {}
    for p in profiles:
        formats[p["format"]] = formats.get(p["format"], 0) + 1
        languages[p["language"]] = languages.get(p["language"], 0) + 1
    return {"documents": len(profiles), "total_chars": sum(p["chars"] for p in profiles),
            "total_words": sum(p["words"] for p in profiles), "chars": _summary([p["chars"] for p in profiles]),
            "words": _summary([p["words"] for p in profiles]), "formats": formats, "languages": languages,
            "avg_table_line_ratio": round(statistics.fmean(p["table_line_ratio"] for p in profiles), 4)
            if profiles else 0.0,
            "avg_digit_ratio": round(statistics.fmean(p["digit_ratio"] for p in profiles), 4) if profiles else 0.0}


def chunking_profile(lengths: list[int]) -> dict[str, Any]:
    return {"chunks": len(lengths), **{f"chunk_chars_{k}": v for k, v in _summary([float(n) for n in lengths]).items()}}
