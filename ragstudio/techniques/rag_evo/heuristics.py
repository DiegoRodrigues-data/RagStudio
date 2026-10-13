"""RAG-EVO confidence heuristics. Ported unchanged in behaviour from `ragkit/evo_heuristics.py`.

    confidence = alpha * len + beta * entropy + gamma * coverage      (each term in 0..1)
"""
from __future__ import annotations

import math
import re

_STOP = frozenset("""a o os as um uma uns umas de da do das dos e ou em no na nos nas para por com sem que se é são
ser foi como ao à às aos mais menos muito muita muitos muitas já não sim também até entre sobre quando onde qual
quais""".split())


def tokens(text: str) -> list[str]:
    found = re.findall(r"[a-záàâãéêíóôõúç0-9]+", (text or "").lower(), flags=re.UNICODE)
    return [t for t in found if t not in _STOP and len(t) >= 3]


def score_len(answer: str, target_chars: int = 800) -> float:
    return min(1.0, len(answer or "") / float(target_chars)) if answer else 0.0


def score_entropy(answer: str) -> float:
    """Unigram entropy normalized by log(vocabulary)."""
    toks = tokens(answer)
    if not toks:
        return 0.0
    freq: dict[str, int] = {}
    for tok in toks:
        freq[tok] = freq.get(tok, 0) + 1
    if len(freq) < 2:
        return 0.0
    entropy = -sum((c / len(toks)) * math.log(c / len(toks)) for c in freq.values())
    return max(0.0, min(1.0, entropy / math.log(len(freq))))


def score_coverage(answer: str, context_texts: list[str]) -> float:
    """Share of the answer terms present in the context, normalized by the answer size (min 8 terms)."""
    answer_terms = set(tokens(answer))
    context_terms = set(tokens("\n".join(text[:4000] for text in context_texts[:12])))
    if not answer_terms or not context_terms:
        return 0.0
    return max(0.0, min(1.0, len(answer_terms & context_terms) / max(8, len(answer_terms))))


def confidence_score(answer: str, context_texts: list[str], alpha: float = 0.34, beta: float = 0.33,
                     gamma: float = 0.33, target_chars: int = 800) -> dict[str, float]:
    clamp = lambda v: max(0.0, min(1.0, v))  # noqa: E731
    parts = {"len": score_len(answer, target_chars), "entropy": score_entropy(answer),
             "coverage": score_coverage(answer, context_texts)}
    total = clamp(alpha) * parts["len"] + clamp(beta) * parts["entropy"] + clamp(gamma) * parts["coverage"]
    return {"confidence": round(clamp(total), 6), **{k: round(v, 6) for k, v in parts.items()}}
