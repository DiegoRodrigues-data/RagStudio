"""Ollama endpoint builder: uses the OpenAI-compatible /v1 routes, usually http://localhost:11434."""
from __future__ import annotations

from ..config.loader import Config
from ..core.errors import ConfigError
from .base import Endpoint
from .lmstudio import normalize_local_base


def endpoint(cfg: Config, model: str) -> Endpoint:
    base = cfg.get("ollama", "base_url")
    if not base:
        raise ConfigError("Ollama base_url is not configured ([ollama] base_url)")
    return Endpoint(provider="ollama", model=model, base_url=normalize_local_base(base))
