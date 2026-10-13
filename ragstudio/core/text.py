"""Small text helpers shared by retrieval, evaluation and the mock provider."""
from __future__ import annotations

import re
import unicodedata

_WORD = re.compile(r"\w+", re.UNICODE)
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")

STOPWORDS = frozenset("""
a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sobre entre e ou que se como qual quais
quando onde quem foi é são ser ao aos à às the of and or to in on for with by is are was were what which who when where
how a an it this that these those be as at from
""".split())


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Lowercase, accent-free, single-spaced."""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


def tokenize(text: str) -> list[str]:
    return _WORD.findall(strip_accents(text).lower())


def content_tokens(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in STOPWORDS and len(t) > 1]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text) if s.strip()]


def overlap(query: str, text: str) -> float:
    """Fraction of the query content tokens present in `text` (0..1)."""
    q = set(content_tokens(query))
    if not q:
        return 0.0
    return len(q & set(content_tokens(text))) / len(q)
