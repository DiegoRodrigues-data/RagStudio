"""Optional LLM judge. Off by default; when on, the judge model and prompt hash are stored with every score.

With the mock provider the "judge" is a lexical rule: its scores only validate plumbing and are labeled `mock-llm`.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.errors import ProviderError
from ..prompts import PromptSet
from ..providers import routing
from ..providers.base import Endpoint


def parse_score(raw: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", raw or "")
    if not match:
        return None
    value = float(match.group(0).replace(",", "."))
    return max(0.0, min(1.0, value if value <= 1 else value / 10 if value <= 10 else value / 100))


class Judge:
    def __init__(self, endpoint: Endpoint, language: str = "pt", seed: int | None = 42, timeout: int = 120) -> None:
        self.endpoint = endpoint
        self.prompts = PromptSet(language)
        self.seed = seed
        self.timeout = timeout
        self.usage = {"llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def _score(self, task: str, **variables: Any) -> float | None:
        prompt = self.prompts.render(task, **variables)
        try:
            result = routing.chat(self.endpoint, prompt.messages(), temperature=0.0, max_tokens=16, seed=self.seed,
                                  task=task, inputs=variables, timeout=self.timeout)
        except ProviderError:
            return None
        self.usage["llm_calls"] += 1
        self.usage["prompt_tokens"] += result.prompt_tokens
        self.usage["completion_tokens"] += result.completion_tokens
        return parse_score(result.text)

    def prompt_hash(self) -> str:
        return self.prompts.template_hash("judge_accuracy")[:16] + "+" + self.prompts.template_hash(
            "judge_faithfulness")[:16]

    def evaluate(self, question: str, answer: str, context: str, expected: str | None) -> dict[str, Any]:
        out: dict[str, Any] = {"judge_model": self.endpoint.model, "judge_prompt_sha256": self.prompt_hash(),
                               "judge_accuracy": None, "judge_faithfulness": None}
        if not answer.strip():
            return out
        out["judge_faithfulness"] = self._score("judge_faithfulness", query=question, answer=answer,
                                                context=context[:12000])
        if expected and expected.strip():
            out["judge_accuracy"] = self._score("judge_accuracy", query=question, answer=answer, expected=expected)
        return out
