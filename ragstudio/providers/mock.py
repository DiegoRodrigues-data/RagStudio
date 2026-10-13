"""Deterministic offline provider (RAGSTUDIO_PROVIDER=mock).

Embeddings: hashed bag-of-words, so texts sharing words are close. Chat: one small rule per prompt task, computed
from the task inputs, so every technique can be exercised end to end without a model. Adapted from
`_mock_vector` / `_mock_chat` in ../JudDoc_Ex/Backend/rag/providers.py.

Nothing here measures model quality: results obtained with this provider only validate plumbing.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable
from typing import Any

from ..core.text import content_tokens, overlap, split_sentences

MOCK_LLM = "mock-llm"
MOCK_EMBEDDING = "mock-embed"
REFUSAL = "Não encontrei essa informação no contexto."

_PASSAGE = re.compile(r"^\[(\d+)\] \([^)]*\)\n", re.M)
_MARK = re.compile(r"\s*\[\d+\]")
_ENTITY = re.compile(r"\b[A-ZÀ-Ý][\wÀ-ÿ]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][\wÀ-ÿ]+)*")


def mock_vector(text: str, dim: int = 96) -> list[float]:
    vec = [0.0] * dim
    for tok in content_tokens(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0 if (h >> 8) % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


def mock_embed(texts: list[str], dim: int = 96) -> list[list[float]]:
    return [mock_vector(t, dim) for t in texts]


def _best_sentences(query: str, text: str, limit: int, minimum: float = 0.0) -> list[tuple[float, str]]:
    scored = [(overlap(query, s), s) for s in split_sentences(text)]
    scored = [(score, s) for score, s in scored if score > minimum]
    return sorted(scored, key=lambda item: -item[0])[:limit]


def _answer(v: dict[str, Any]) -> str:
    query, context = str(v.get("query", "")), str(v.get("context", ""))
    best: tuple[float, str, str] | None = None
    parts = _PASSAGE.split(context)  # ['', '1', body, '2', body, ...]
    for n, body in zip(parts[1::2], parts[2::2], strict=False):
        for score, sentence in _best_sentences(query, body, 1):
            if best is None or score > best[0]:
                best = (score, sentence, n)
    if best is None:
        return REFUSAL
    return f"{best[1][:400]} [{best[2]}]"


def _multi_queries(v: dict[str, Any]) -> str:
    query, n = str(v.get("query", "")), int(v.get("n", 4))
    toks = content_tokens(query)
    half = max(1, len(toks) // 2)
    variants = [" ".join(toks), " ".join(toks[:half]), " ".join(toks[half:]) or " ".join(toks),
                " ".join(sorted(toks, key=lambda t: (-len(t), t))[:3]), " ".join(reversed(toks))]
    return "\n".join(list(dict.fromkeys(x for x in variants if x))[:n])


def _decompose(v: dict[str, Any]) -> str:
    query, n = str(v.get("query", "")), int(v.get("n", 4))
    parts = [p.strip(" ?") for p in re.split(r"\s+e\s+|\s+and\s+|;|,", query) if len(p.strip()) > 3]
    if len(parts) < 2:
        parts = [query.strip(), " ".join(content_tokens(query))]
    return "\n".join(f"{p}?" if not p.endswith("?") else p for p in parts[:n])


def _extract(v: dict[str, Any]) -> str:
    return " ".join(s for _, s in _best_sentences(str(v.get("query", "")), str(v.get("text", "")), 2))


def _gap_query(v: dict[str, Any]) -> str:
    query_toks = content_tokens(str(v.get("query", "")))
    extra = [t for t in content_tokens(str(v.get("answer", ""))) if t not in query_toks]
    return " ".join(query_toks + list(dict.fromkeys(extra))[:4])


def _rerank(v: dict[str, Any]) -> str:
    query, passages = str(v.get("query", "")), list(v.get("passages", []))
    order = sorted(range(len(passages)), key=lambda i: (-overlap(query, str(passages[i])), i))
    return ",".join(str(i + 1) for i in order)


def _confidence(v: dict[str, Any]) -> str:
    answer = str(v.get("answer", ""))
    if not answer or answer.startswith(REFUSAL[:12]):
        return "0.1"
    return f"{0.3 + 0.7 * overlap(str(v.get('query', '')), answer):.2f}"


def _step_back(v: dict[str, Any]) -> str:
    toks = sorted(content_tokens(str(v.get("query", ""))), key=lambda t: (-len(t), t))[:3]
    return f"Qual é o contexto geral sobre {' '.join(toks)}?"


def _relevance(v: dict[str, Any]) -> str:
    return "sim" if overlap(str(v.get("query", "")), str(v.get("text", ""))) >= 0.34 else "não"


def _context_prefix(v: dict[str, Any]) -> str:
    first = split_sentences(str(v.get("document", "")))
    return (first[0][:160] if first else "").lstrip("# ").strip()


def _summarize(v: dict[str, Any]) -> str:
    return " ".join(split_sentences(str(v.get("text", "")))[:3])[:500]


def _entities(v: dict[str, Any]) -> str:
    found = [m.group(0).strip() for m in _ENTITY.finditer(str(v.get("text", "")))]
    return "\n".join(list(dict.fromkeys(e for e in found if len(e) > 3))[:12])


def _question_parts(query: str) -> list[str]:
    parts = [p.strip(" ?") for p in re.split(r"\s+e\s+|\s+and\s+|;", query) if len(p.strip()) > 3]
    return [f"{p}?" for p in parts] if len(parts) > 1 else [query.strip()]


def _kg_extract(v: dict[str, Any]) -> str:
    """Capitalized names are entities; names sharing a sentence are related."""
    lines: list[str] = []
    seen: set[str] = set()
    limit = int(v.get("max_entities", 12))
    for sentence in split_sentences(str(v.get("text", ""))):
        names = list(dict.fromkeys(m.group(0).strip() for m in _ENTITY.finditer(sentence)
                                   if len(m.group(0).strip()) > 3))
        names = [n for n in names if n in seen or len(seen) < limit]
        for name in names:
            if name not in seen:
                seen.add(name)
                lines.append(f"ENTITY | {name} | conceito | {sentence[:120]}")
        lines.extend(f"REL | {a} | {b} | relacionado a | {sentence[:160]}"
                     for a, b in zip(names, names[1:], strict=False))
    return "\n".join(lines)


def _community_report(v: dict[str, Any]) -> str:
    entities, relations = list(v.get("entities", [])), list(v.get("relations", []))
    names = [str(e).split(" (")[0] for e in entities[:3]]
    body = " ".join(str(r) for r in (relations or entities)[:4])
    return f"Comunidade: {', '.join(names)}\n{body[:600]}"


def _community_points(v: dict[str, Any]) -> str:
    query, report = str(v.get("query", "")), str(v.get("report", ""))
    best = _best_sentences(query, report, 2)
    if not best:
        return "SCORE: 0"
    return f"SCORE: {round(100 * overlap(query, report))}\n" + "\n".join(s for _, s in best)


def _lightrag_keywords(v: dict[str, Any]) -> str:
    query = str(v.get("query", ""))
    toks = content_tokens(query)
    names = [m.group(0) for m in _ENTITY.finditer(query) if len(m.group(0)) > 3][1:]
    high = sorted(toks, key=lambda t: (-len(t), t))[:2]
    return f"HIGH: {', '.join(high)}\nLOW: {', '.join(list(dict.fromkeys(names + toks)))}"


def _support(v: dict[str, Any]) -> str:
    answer, passage = _MARK.sub("", str(v.get("answer", ""))), str(v.get("passage", ""))
    share = overlap(answer, passage)
    level = "full" if share >= 0.6 else "partial" if share >= 0.3 else "none"
    return f"SUPPORT: {level}\nUSEFUL: {1 + round(4 * overlap(str(v.get('query', '')), answer))}"


def _rank_passages(v: dict[str, Any]) -> str:
    query = str(v.get("query", ""))
    return "\n".join(f"{i}: {round(10 * overlap(query, str(p)))}" for i, p in enumerate(v.get("passages", []), 1))


def _complexity(v: dict[str, Any]) -> str:
    query = str(v.get("query", ""))
    if len(content_tokens(query)) < 2:
        return "A"
    return "C" if len(_question_parts(query)) > 1 else "B"


def _next_hop(v: dict[str, Any]) -> str:
    parts, hop = _question_parts(str(v.get("query", ""))), int(v.get("hop", 1))
    return parts[hop - 1] if hop <= len(parts) else "DONE"


def _hop_answer(v: dict[str, Any]) -> str:
    answer = _MARK.sub("", _answer(v)).strip()
    return "não encontrado" if answer == REFUSAL else answer


def _recomp_summary(v: dict[str, Any]) -> str:
    query = str(v.get("query", ""))
    best = _best_sentences(query, " ".join(str(p) for p in v.get("passages", [])), 2, minimum=0.2)
    return " ".join(s for _, s in best) or "NONE"


def _agent_plan(v: dict[str, Any]) -> str:
    return "\n".join(f"Buscar: {p}" for p in _question_parts(str(v.get("query", "")))[:int(v.get("n", 3))])


def _agent_step(v: dict[str, Any]) -> str:
    step, max_steps = int(v.get("step", 1)), int(v.get("max_steps", 4))
    query = str(v.get("query", ""))
    if step == 1:
        return json.dumps({"tool": "search", "arguments": {"query": query}}, ensure_ascii=False)
    if step == 2 and max_steps > 2:
        return json.dumps({"tool": "keyword_search", "arguments": {"query": " ".join(content_tokens(query))}},
                          ensure_ascii=False)
    if step == 3 and max_steps > 3:
        return json.dumps({"tool": "read_more", "arguments": {"passage": 1}})
    return json.dumps({"tool": "finish", "arguments": {}})


def _f1(a: str, b: str) -> float:
    ta, tb = content_tokens(a), content_tokens(b)
    common = len(set(ta) & set(tb))
    if not ta or not tb or not common:
        return 0.0
    p, r = common / len(set(ta)), common / len(set(tb))
    return 2 * p * r / (p + r)


def _judge_accuracy(v: dict[str, Any]) -> str:
    return f"{_f1(str(v.get('answer', '')), str(v.get('expected', ''))):.2f}"


def _judge_faithfulness(v: dict[str, Any]) -> str:
    toks = set(content_tokens(str(v.get("answer", ""))))
    ctx = set(content_tokens(str(v.get("context", ""))))
    return f"{(len(toks & ctx) / len(toks)) if toks else 0.0:.2f}"


def _hypo_doc(v: dict[str, Any]) -> str:
    query = str(v.get("query", ""))
    return f"{' '.join(content_tokens(query))}. {query}"


_RULES: dict[str, Callable[[dict[str, Any]], str]] = {
    "answer": _answer, "multi_queries": _multi_queries, "hypo_doc": _hypo_doc, "decompose": _decompose,
    "extract_essential": _extract, "gap_query": _gap_query, "rerank": _rerank, "confidence": _confidence,
    "step_back": _step_back, "relevance": _relevance, "context_prefix": _context_prefix, "summarize": _summarize,
    "entities": _entities, "judge_accuracy": _judge_accuracy, "judge_faithfulness": _judge_faithfulness,
    "kg_extract": _kg_extract, "community_report": _community_report, "community_points": _community_points,
    "lightrag_keywords": _lightrag_keywords, "needs_retrieval": lambda v: "sim",
    "answer_direct": lambda v: f"Resposta direta, sem consulta a documentos: {v.get('query', '')}",
    "support": _support, "rank_passages": _rank_passages, "complexity": _complexity, "next_hop": _next_hop,
    "hop_answer": _hop_answer, "recomp_summary": _recomp_summary, "agent_plan": _agent_plan, "agent_step": _agent_step,
    "agent_step_text": _agent_step,
}


def mock_tool_calls(text: str) -> tuple[dict[str, Any], ...]:
    """A rule that answers `{"tool": name, "arguments": {...}}` is delivered as a native tool call."""
    try:
        data = json.loads(text)
    except ValueError:
        return ()
    if not isinstance(data, dict) or not data.get("tool"):
        return ()
    return ({"name": str(data["tool"]), "arguments": dict(data.get("arguments") or {})},)


def mock_chat(messages: list[dict[str, str]], task: str | None = None, inputs: dict[str, Any] | None = None) -> str:
    """Rule for `task` applied to `inputs`; an unknown task echoes the best sentence of the user message."""
    rule = _RULES.get(task or "")
    if rule is not None:
        return rule(inputs or {})
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    sentences = split_sentences(user)
    return sentences[0][:300] if sentences else ""
