from __future__ import annotations
from typing import List, Dict, Any, Tuple
import math
import re

Doc = Dict[str, Any]

_STOP = {
    "a","o","os","as","um","uma","uns","umas","de","da","do","das","dos","e","ou","em","no","na","nos","nas",
    "para","por","com","sem","que","se","é","são","ser","foi","como","ao","à","às","aos","mais","menos","muito",
    "muita","muitos","muitas","já","não","sim","também","até","entre","sobre","quando","onde","qual","quais"
}

def _tokens(text: str) -> List[str]:
    text = (text or "").lower()
    toks = re.findall(r"[a-záàâãéêíóôõúç0-9]+", text, flags=re.UNICODE)
    return [t for t in toks if t not in _STOP and len(t) >= 3]

def score_len(answer: str, *, target_chars: int = 800) -> float:
    n = len(answer or "")
    if n <= 0:
        return 0.0
    return min(1.0, n / float(target_chars))

def score_entropy(answer: str) -> float:
    toks = _tokens(answer)
    if not toks:
        return 0.0
    # unigram entropy normalized by log(V)
    freq = {}
    for t in toks:
        freq[t] = freq.get(t, 0) + 1
    total = len(toks)
    ent = 0.0
    for c in freq.values():
        p = c / total
        ent -= p * math.log(p + 1e-12)
    V = max(1, len(freq))
    return max(0.0, min(1.0, ent / math.log(V + 1e-12)))

def score_coverage(answer: str, docs: List[Doc]) -> float:
    """
    Cobertura simples: overlap de termos (answer vs contexto).
    Retorna 0..1.
    """
    a = set(_tokens(answer))
    if not a:
        return 0.0
    ctx_text = "\n".join((d.get("text","") or "")[:4000] for d in docs[:12])
    c = set(_tokens(ctx_text))
    if not c:
        return 0.0
    inter = len(a.intersection(c))
    # normaliza por tamanho do answer para evitar inflar com contexto gigante
    return max(0.0, min(1.0, inter / max(8, len(a))))

def confidence_score(
    answer: str,
    docs: List[Doc],
    *,
    alpha: float = 0.34,
    beta: float = 0.33,
    gamma: float = 0.33,
    target_chars: int = 800,
) -> float:
    """
    Score composto em 0..1 inspirado na fórmula len + entropy + coverage.
    """
    alpha = max(0.0, min(1.0, alpha))
    beta  = max(0.0, min(1.0, beta))
    gamma = max(0.0, min(1.0, gamma))
    s_len = score_len(answer, target_chars=target_chars)
    s_ent = score_entropy(answer)
    s_cov = score_coverage(answer, docs)
    s = alpha*s_len + beta*s_ent + gamma*s_cov
    return max(0.0, min(1.0, s))
