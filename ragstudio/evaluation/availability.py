"""What can be measured for a run, and what cannot without annotation. No metric is ever invented.

- efficiency (latency, tokens, calls, cost) and context-based generation metrics need nothing;
- retrieval metrics need gold passages;
- accuracy metrics need an expected answer;
- judge metrics need the judge enabled (and, for accuracy, an expected answer).
"""
from __future__ import annotations

from typing import Any

EFFICIENCY = ("latency_total", "latency_by_stage", "prompt_tokens", "completion_tokens", "llm_calls", "cost_usd")
CONTEXT_BASED = ("faithfulness", "groundedness", "citation_accuracy", "hallucination", "refusal")
RETRIEVAL = ("hit", "recall", "precision", "mrr", "ndcg", "context_coverage")
ACCURACY = ("exact_match", "f1", "accuracy")


def question_flags(question: dict[str, Any]) -> dict[str, bool]:
    return {"has_gold_passages": bool(question.get("gold_passages")),
            "has_expected_answer": bool((question.get("expected_answer") or "").strip())}


def availability(questions: list[dict[str, Any]], judge: bool = False) -> dict[str, Any]:
    flags = [question_flags(q) for q in questions]
    n = len(flags)
    with_gold = sum(f["has_gold_passages"] for f in flags)
    with_expected = sum(f["has_expected_answer"] for f in flags)
    available = [*EFFICIENCY, *CONTEXT_BASED]
    requires: dict[str, str] = {}
    partial: dict[str, str] = {}
    for names, count, need in ((RETRIEVAL, with_gold, "gold passages"), (ACCURACY, with_expected, "expected answer")):
        if count == 0:
            requires.update({name: f"needs {need} (0 of {n} questions annotated)" for name in names})
        else:
            available.extend(names)
            if count < n:
                partial.update({name: f"computed on {count} of {n} questions (the others lack {need})"
                                for name in names})
    if judge:
        available.append("judge_faithfulness")
        if with_expected:
            available.append("judge_accuracy")
        else:
            requires["judge_accuracy"] = f"needs expected answer (0 of {n} questions annotated)"
    else:
        requires["judge_accuracy"] = "LLM judge disabled (evaluation.judge = true to enable)"
        requires["judge_faithfulness"] = "LLM judge disabled (evaluation.judge = true to enable)"
    requires["human_agreement"] = "needs human reviews (`evaluate review add`)"
    return {"questions": n, "with_gold_passages": with_gold, "with_expected_answer": with_expected,
            "available": available, "partial": partial, "requires_annotation": requires}
