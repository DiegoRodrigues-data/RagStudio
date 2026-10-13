"""Provider-neutral records. A provider is selected by `Endpoint.provider`; calls go through `routing`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Endpoint:
    provider: str  # mock | openai | lmstudio | ollama
    model: str
    base_url: str = ""
    api_key: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def is_local(self) -> bool:
        return self.provider in ("mock", "lmstudio", "ollama")

    def public(self) -> dict[str, Any]:
        """Safe to persist: never includes the API key."""
        return {"provider": self.provider, "model": self.model, "base_url": self.base_url,
                "has_api_key": bool(self.api_key)}


@dataclass(frozen=True)
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    latency: float
    usage_reported: bool = True  # False when token counts were estimated (API returned no usage)
    system_fingerprint: str = ""
    finish_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    tool_calls: tuple[dict[str, Any], ...] = ()  # [{"name", "arguments": dict}] when tools were offered


@dataclass(frozen=True)
class EmbedResult:
    vectors: list[list[float]]
    tokens: int
    model: str
    latency: float
    usage_reported: bool = True
    cache_hits: int = 0


def estimate_tokens(text: str) -> int:
    """Rough fallback (4 chars per token) used only when the API reports no usage; flagged as estimated."""
    return max(1, len(text) // 4) if text else 0
