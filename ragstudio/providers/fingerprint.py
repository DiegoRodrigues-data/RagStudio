"""Model version identification stored in the environment snapshot of every run.

API providers expose `system_fingerprint` (when they do); local servers do not, so an optional probe hashes the
answer to a fixed prompt at temperature 0. The probe costs one call and is off by default
([experiments] fingerprint_probe).
"""
from __future__ import annotations

from typing import Any

from ..core.errors import ProviderError
from ..core.hashing import sha256_text
from . import routing
from .base import Endpoint

PROBE = "Complete with exactly five words: The capital of France is"


def model_fingerprint(ep: Endpoint, probe: bool = False, seed: int | None = None) -> dict[str, Any]:
    info: dict[str, Any] = {"provider": ep.provider, "model": ep.model, "base_url": ep.base_url,
                            "system_fingerprint": "", "probe_sha256": None}
    if ep.provider == "mock":
        info["system_fingerprint"] = "mock-v1"
        return info
    if not probe:
        return info
    try:
        result = routing.chat(ep, [{"role": "user", "content": PROBE}], max_tokens=16, seed=seed, max_retries=1)
        info["system_fingerprint"] = result.system_fingerprint
        info["probe_sha256"] = sha256_text(result.text.strip())
        info["reported_model"] = result.model
    except ProviderError as exc:
        info["probe_error"] = str(exc)
    return info
