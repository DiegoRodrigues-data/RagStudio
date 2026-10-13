"""Generation metrics. Ported from the Level 2 / Level 3 evaluators of JudDoc_Ex (`experiments/evaluator.py`).

Context-based (always available): faithfulness, groundedness, citation_accuracy, hallucination, refusal.
Reference-based (need an expected answer): exact_match, f1, accuracy. Without an expected answer they are None.

These are lexical heuristics: cheap, deterministic and reproducible, but they do not understand paraphrase. Use the
LLM judge (`judge.py`) or human review for claims about answer quality.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.text import content_tokens, normalize, split_sentences

OUTSIDE_KNOWLEDGE = ("com base em meu conhecimento", "com base no meu conhecimento", "geralmente", "tipicamente",
                     "normalmente", "é comum que", "based on my knowledge", "generally speaking", "typically")
REFUSALS = ("não posso responder", "não tenho informação suficiente", "o contexto não contém",
            "não encontrei no documento", "não está claro no texto", "não encontrei essa informação",
            "não encontrei a informação", "não foi possível encontrar", "information was not found",
            "the context does not contain", "i cannot answer", "not enough information")
_POSITIVE = {"sim", "yes", "verdadeiro", "true"}
_NEGATIVE = {"não", "nao", "no", "falso", "false"}
_MARKER = re.compile(r"\[(\d+)\]")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_PASSAGE = re.compile(r"^\[(\d+)\] \([^)]*\)\n", re.M)


def is_refusal(answer: str) -> bool:
    low = answer.lower()
    return any(phrase in low for phrase in REFUSALS)


def f1_tokens(answer: str, expected: str) -> float:
    a, e = set(content_tokens(answer)), set(content_tokens(expected))
    common = len(a & e)
    if not a or not e or not common:
        return 0.0
    precision, recall = common / len(a), common / len(e)
    return 2 * precision * recall / (precision + recall)


def bool_sign(text: str) -> bool | None:
    words = {w.strip(".,!?;:*") for w in text.lower().split()}
    positive, negative = bool(words & _POSITIVE), bool(words & _NEGATIVE)
    if positive != negative:
        return positive
    return None


def _strip_markers(text: str) -> str:
    return _MARKER.sub("", text)


def _grounded_share(answer: str, context: str, min_chars: int, threshold: float) -> float | None:
    """Share of answer sentences whose word trigrams appear in the context at least `threshold` of the time."""
    ctx = normalize(context)
    sentences = [s for s in split_sentences(_strip_markers(answer)) if len(s) > min_chars]
    if not sentences or not ctx:
        return None
    grounded = 0
    for sentence in sentences:
        words = normalize(sentence).split()
        trigrams = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
        if trigrams and sum(1 for t in trigrams if t in ctx) >= len(trigrams) * threshold:
            grounded += 1
    return grounded / len(sentences)


def faithfulness(answer: str, context: str) -> float | None:
    base = _grounded_share(answer, context, 20, 0.3)
    if base is None:
        return None
    penalty = min(sum(1 for p in OUTSIDE_KNOWLEDGE if p in answer.lower()) * 0.15, 0.5)
    return round(max(0.0, min(1.0, base - penalty)), 4)


def groundedness(answer: str, context: str) -> float | None:
    share = _grounded_share(answer, context, 15, 0.25)
    return None if share is None else round(share, 4)


def context_passages(context: str) -> dict[int, str]:
    parts = _PASSAGE.split(context)
    return {int(n): body for n, body in zip(parts[1::2], parts[2::2], strict=False)}


def citation_accuracy(answer: str, context: str) -> float | None:
    """Share of `[n]` markers that point to an existing passage sharing content with the citing sentence.
    None when the answer cites nothing (no claim about citation quality can be made)."""
    passages = context_passages(context)
    checked = correct = 0
    sentences: list[str] = []
    for piece in split_sentences(answer):  # a marker written after the full stop belongs to the previous sentence
        if sentences and not content_tokens(_strip_markers(piece)):
            sentences[-1] += " " + piece
        else:
            sentences.append(piece)
    for sentence in sentences:
        markers = [int(m) for m in _MARKER.findall(sentence)]
        if not markers:
            continue
        tokens = set(content_tokens(_strip_markers(sentence)))
        for n in markers:
            checked += 1
            passage_tokens = set(content_tokens(passages.get(n, "")))
            if tokens and passage_tokens and len(tokens & passage_tokens) / len(tokens) >= 0.3:
                correct += 1
    return round(correct / checked, 4) if checked else None


def hallucination(answer: str, context: str) -> float:
    """1.0 when the answer appeals to outside knowledge or states numbers absent from the context."""
    low = answer.lower()
    if any(phrase in low for phrase in OUTSIDE_KNOWLEDGE):
        return 1.0
    context_numbers = set(_NUMBER.findall(context))
    answer_numbers = _NUMBER.findall(_strip_markers(answer))
    return 1.0 if any(n not in context_numbers for n in answer_numbers) else 0.0


def accuracy(answer: str, expected: str, answer_type: str) -> float:
    if answer_type == "boolean":
        a, e = bool_sign(answer), bool_sign(expected)
        if a is not None and e is not None:
            return 1.0 if a == e else 0.0
    if answer_type == "classification" and normalize(expected) in normalize(answer):
        return 1.0
    return f1_tokens(answer, expected)


def exact_match(answer: str, expected: str, answer_type: str) -> float:
    if answer_type == "boolean":
        a, e = bool_sign(answer), bool_sign(expected)
        return 1.0 if a is not None and a == e else 0.0
    return 1.0 if normalize(expected).rstrip(".") in normalize(_strip_markers(answer)) else 0.0


def evaluate(answer: str, context: str, expected: str | None, answer_type: str = "extraction") -> dict[str, Any]:
    out: dict[str, Any] = {
        "faithfulness": faithfulness(answer, context), "groundedness": groundedness(answer, context),
        "citation_accuracy": citation_accuracy(answer, context), "hallucination": hallucination(answer, context),
        "refusal": 1.0 if is_refusal(answer) else 0.0, "exact_match": None, "f1": None, "accuracy": None,
    }
    if expected and expected.strip():
        out["exact_match"] = exact_match(answer, expected, answer_type)
        out["f1"] = round(f1_tokens(answer, expected), 4)
        out["accuracy"] = round(accuracy(answer, expected, answer_type), 4)
    return out
