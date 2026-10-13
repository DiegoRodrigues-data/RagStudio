from __future__ import annotations
from typing import List
import math

def _dot(a: List[float], b: List[float]) -> float:
    return sum(x*y for x, y in zip(a, b))

def _norm(a: List[float]) -> float:
    return math.sqrt(sum(x*x for x in a))

def cosine(a: List[float], b: List[float]) -> float:
    na = _norm(a)
    nb = _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)

def mmr_select(query_emb: List[float], doc_embs: List[List[float]], k: int, lambda_: float = 0.5) -> List[int]:
    """
    Maximal Marginal Relevance selection.
    Retorna índices selecionados (no espaço doc_embs).
    """
    if k <= 0 or not doc_embs:
        return []
    k = min(k, len(doc_embs))
    lambda_ = max(0.0, min(1.0, lambda_))

    sim_q = [cosine(query_emb, e) for e in doc_embs]

    selected: List[int] = []
    remaining = set(range(len(doc_embs)))

    # first: max similarity to query
    first = max(remaining, key=lambda i: sim_q[i])
    selected.append(first)
    remaining.remove(first)

    while len(selected) < k and remaining:
        def mmr_score(i: int) -> float:
            # max similarity to already selected (diversity penalty)
            max_sim_sel = max(cosine(doc_embs[i], doc_embs[j]) for j in selected) if selected else 0.0
            return lambda_ * sim_q[i] - (1.0 - lambda_) * max_sim_sel

        nxt = max(remaining, key=mmr_score)
        selected.append(nxt)
        remaining.remove(nxt)

    return selected
