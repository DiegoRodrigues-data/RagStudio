from __future__ import annotations
from typing import Any, Dict, Optional, Callable, Tuple
import json
import os
from datetime import datetime

LLM = Callable[[str], str]

def heuristic_confidence(answer: str, *, min_len: int = 250) -> float:
    """Heurística simples: respostas muito curtas tendem a ter baixa confiança."""
    if not answer:
        return 0.0
    if len(answer) >= min_len:
        return 0.75
    return 0.4

def llm_confidence(llm: LLM, *, query: str, answer: str, context: str, timeout_safe_default: float = 0.5) -> float:
    """Pede para a própria LLM dar uma nota 0..1 (fallback se falhar)."""
    prompt = (
        "Avalie a CONFIANÇA da RESPOSTA em relação ao CONTEXTO e à PERGUNTA.\n"
        "Retorne APENAS um número de 0.0 a 1.0.\n\n"
        f"PERGUNTA: {query}\n\n"
        f"CONTEXTO (resumido):\n{context[:4000]}\n\n"
        f"RESPOSTA:\n{answer[:4000]}\n"
    )
    try:
        raw = llm(prompt).strip()
        m = raw.split()[0]
        v = float(m)
        if v < 0.0: v = 0.0
        if v > 1.0: v = 1.0
        return v
    except Exception:
        return timeout_safe_default

def log_rag_evo(
    *,
    query: str,
    answer: str,
    confidence: float,
    diagnostics: Dict[str, Any],
    feedback: Optional[str] = None,
    log_dir: str = "logs",
    filename: str = "rag_evo_log.jsonl",
) -> str:
    os.makedirs(log_dir, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "answer": answer,
        "confidence_score": confidence,
        "feedback": feedback,
        "needs_review": confidence < 0.6,
        "diagnostics": diagnostics,
    }
    path = os.path.join(log_dir, filename)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
