"""Prompt rendering: `PromptSet(language).render(task, **variables)` -> RenderedPrompt with stable hashes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.errors import ValidationError
from ..core.hashing import sha256_text
from .templates import PROMPT_SET_VERSION, SYSTEM, TEMPLATES


@dataclass(frozen=True)
class RenderedPrompt:
    task: str
    system: str
    user: str
    template_sha256: str  # hash of system + template: identifies the prompt version independently of the inputs

    def messages(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.system}, {"role": "user", "content": self.user}]


def _as_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "\n".join(f"[{i}] {item}" for i, item in enumerate(value, 1))
    return str(value)


class PromptSet:
    def __init__(self, language: str = "pt", overrides: dict[str, str] | None = None) -> None:
        if language not in TEMPLATES:
            raise ValidationError(f"no prompt templates for language '{language}' (available: {sorted(TEMPLATES)})")
        self.language = language
        self.version = PROMPT_SET_VERSION
        self._templates = {**TEMPLATES[language], **(overrides or {})}
        self._system = SYSTEM[language]

    def tasks(self) -> list[str]:
        return sorted(self._templates)

    def system(self, task: str) -> str:
        return self._system.get(task, self._system["_default"])

    def template(self, task: str) -> str:
        if task not in self._templates:
            raise ValidationError(f"unknown prompt task '{task}' (available: {self.tasks()})")
        return self._templates[task]

    def template_hash(self, task: str) -> str:
        return sha256_text(self.system(task) + "\n---\n" + self.template(task))

    def render(self, task: str, **variables: Any) -> RenderedPrompt:
        template = self.template(task)
        try:
            user = template.format(**{k: _as_text(v) for k, v in variables.items()})
        except KeyError as exc:
            raise ValidationError(f"prompt '{task}' is missing variable {exc}") from exc
        return RenderedPrompt(task=task, system=self.system(task), user=user,
                              template_sha256=self.template_hash(task))
