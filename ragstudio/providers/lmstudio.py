"""LM Studio (0.3+) endpoint builder: OpenAI-compatible server, usually http://localhost:1234."""
from __future__ import annotations

from ..config.loader import Config
from ..core.errors import ConfigError
from .base import Endpoint


def normalize_local_base(url: str) -> str:
    """Local URLs always end in /v1 (`http://localhost:1234` -> `http://localhost:1234/v1`)."""
    url = url.strip().rstrip("/")
    return url if url.endswith("/v1") else url + "/v1"


def endpoint(cfg: Config, model: str) -> Endpoint:
    base = cfg.get("lm_studio", "base_url")
    if not base:
        raise ConfigError("LM Studio base_url is not configured ([lm_studio] base_url)")
    return Endpoint(provider="lmstudio", model=model, base_url=normalize_local_base(base))
