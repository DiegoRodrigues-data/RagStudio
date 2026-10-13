"""Evaluation: retrieval metrics, generation metrics, optional LLM judge, aggregation and availability."""
from __future__ import annotations

from typing import Any

from . import generation_metrics, retrieval_metrics
from .judge import Judge


def evaluate_result(question: dict[str, Any], answer: str, context_text: str, chunks: list[dict[str, Any]],
                    judge: Judge | None = None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """(retrieval metrics or None, generation metrics) for one answered question."""
    retrieval = retrieval_metrics.evaluate(chunks, question.get("gold_passages") or [], context_text)
    generation = generation_metrics.evaluate(answer, context_text, question.get("expected_answer"),
                                             question.get("answer_type") or "extraction")
    if judge is not None:
        generation.update(judge.evaluate(question["text"], answer, context_text, question.get("expected_answer")))
    return retrieval, generation
