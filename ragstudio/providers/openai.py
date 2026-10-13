"""OpenAI endpoint builder."""
from __future__ import annotations

from ..config.loader import Config
from ..core.errors import ConfigError
from .base import Endpoint

MISSING_KEY = ("OpenAI API key is not configured. Set it with `ragstudio config set --section openai --key api_key "
               "--value sk-...`, configure a local provider URL (LM Studio / Ollama), or use RAGSTUDIO_PROVIDER=mock.")


def endpoint(cfg: Config, model: str) -> Endpoint:
    key = cfg.get("openai", "api_key")
    if not key:
        raise ConfigError(MISSING_KEY)
    return Endpoint(provider="openai", model=model, api_key=key,
                    base_url=cfg.get("openai", "base_url", "https://api.openai.com/v1").rstrip("/"))
