"""Provider routing and the two entry points used by the rest of the system: `chat()` and `embed()`.

Routing rule (same as JudDoc_Ex): RAGSTUDIO_PROVIDER / [provider] default wins; with `auto`, a non-empty LM Studio
URL wins, then Ollama, otherwise OpenAI. With a local provider configured, a model listed in
[openai] models_allowlist still goes to OpenAI when a key exists.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ..config.loader import Config
from ..config.loader import load as load_config
from ..core.errors import ConfigError, ProviderError
from . import lmstudio, mock, ollama, openai, openai_compat
from .base import EmbedResult, Endpoint, LLMResult, estimate_tokens
from .cache import EmbeddingCache

_sleep = time.sleep  # replaced in tests


def resolve_endpoint(kind: str, model: str | None = None, cfg: Config | None = None) -> Endpoint:
    """kind: 'llm' or 'embedding'. `model=None` uses the configured default for that kind."""
    cfg = cfg or load_config()
    provider = cfg.provider()
    if provider == "mock":
        default = mock.MOCK_LLM if kind == "llm" else mock.MOCK_EMBEDDING
        return Endpoint(provider="mock", model=model or default,
                        options={"dim": cfg.get_int("embedding", "mock_dim", 96)})
    model = model or cfg.get("llm" if kind == "llm" else "embedding", "model")
    if not model:
        raise ConfigError(f"no {kind} model configured")
    if provider != "openai" and model in cfg.get_list("openai", "models_allowlist") and cfg.get("openai", "api_key"):
        provider = "openai"
    builder = {"openai": openai.endpoint, "lmstudio": lmstudio.endpoint, "ollama": ollama.endpoint}[provider]
    return builder(cfg, model)


def backoff_seconds(attempt: int, retry_after: float | None = None) -> float:
    return min(retry_after if retry_after else 2.0 ** attempt, 60.0)


def chat(ep: Endpoint, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 1024,
         seed: int | None = None, task: str | None = None, inputs: dict[str, Any] | None = None, timeout: int = 120,
         max_retries: int = 4, on_retry: Callable[[int, ProviderError], None] | None = None,
         tools: list[dict[str, Any]] | None = None) -> LLMResult:
    """One chat completion with retry on 429/5xx. `task` and `inputs` are only read by the mock provider.

    `tools` (OpenAI function schemas) enables native tool calling; the choice comes back in `tool_calls`."""
    if ep.provider == "mock":
        start = time.perf_counter()
        text = mock.mock_chat(messages, task=task, inputs=inputs)
        prompt = " ".join(m["content"] for m in messages)
        calls = mock.mock_tool_calls(text) if tools else ()
        return LLMResult(text="" if calls else text, prompt_tokens=estimate_tokens(prompt),
                         completion_tokens=estimate_tokens(text), model=ep.model,
                         latency=time.perf_counter() - start, usage_reported=True, system_fingerprint="mock-v1",
                         finish_reason="tool_calls" if calls else "stop", tool_calls=calls)
    attempt = 0
    while True:
        try:
            return openai_compat.chat(ep, messages, temperature=temperature, max_tokens=max_tokens, seed=seed,
                                      timeout=timeout, tools=tools)
        except ProviderError as exc:
            attempt += 1
            if not exc.retryable or attempt > max_retries:
                raise
            if on_retry:
                on_retry(attempt, exc)
            _sleep(backoff_seconds(attempt, exc.retry_after))


def embed(ep: Endpoint, texts: list[str], *, batch_size: int = 32, timeout: int = 60, max_retries: int = 4,
          cache: EmbeddingCache | None = None) -> EmbedResult:
    """Embeddings for `texts`, batched, optionally served from the cache (cache hits cost no tokens)."""
    if not texts:
        return EmbedResult(vectors=[], tokens=0, model=ep.model, latency=0.0)
    start = time.perf_counter()
    key = EmbeddingCache.model_key(ep.provider, ep.model)
    cached: list[list[float] | None] = cache.get_many(key, texts) if cache else [None] * len(texts)
    missing = [i for i, v in enumerate(cached) if v is None]
    tokens, reported = 0, True
    for offset in range(0, len(missing), batch_size):
        idx = missing[offset:offset + batch_size]
        batch = [texts[i] for i in idx]
        if ep.provider == "mock":
            vectors = mock.mock_embed(batch, int(ep.options.get("dim", 96)))
            tokens += sum(estimate_tokens(t) for t in batch)
        else:
            result = _embed_with_retry(ep, batch, timeout, max_retries)
            vectors, tokens, reported = result.vectors, tokens + result.tokens, reported and result.usage_reported
        for i, vector in zip(idx, vectors, strict=True):
            cached[i] = vector
        if cache:
            cache.put_many(key, batch, vectors)
    return EmbedResult(vectors=[v for v in cached if v is not None], tokens=tokens, model=ep.model,
                       latency=time.perf_counter() - start, usage_reported=reported,
                       cache_hits=len(texts) - len(missing))


def _embed_with_retry(ep: Endpoint, batch: list[str], timeout: int, max_retries: int) -> EmbedResult:
    attempt = 0
    while True:
        try:
            return openai_compat.embed(ep, batch, timeout=timeout)
        except ProviderError as exc:
            attempt += 1
            if not exc.retryable or attempt > max_retries:
                raise
            _sleep(backoff_seconds(attempt, exc.retry_after))


def list_models(cfg: Config | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    provider = cfg.provider()
    if provider == "mock":
        return {"provider": "mock", "models": [mock.MOCK_LLM, mock.MOCK_EMBEDDING]}
    ep = resolve_endpoint("llm", cfg=cfg)
    return {"provider": ep.provider, "base_url": ep.base_url, "models": openai_compat.list_models(ep)}


def test_connection(cfg: Config | None = None) -> dict[str, Any]:
    """One tiny embedding and one tiny chat call against the saved configuration."""
    cfg = cfg or load_config()
    report: dict[str, Any] = {"provider": cfg.provider()}
    for kind in ("embedding", "llm"):
        try:
            ep = resolve_endpoint(kind, cfg=cfg)
            if kind == "embedding":
                result = embed(ep, ["ping"], max_retries=0)
                report[kind] = {"ok": True, "model": ep.model, "dim": len(result.vectors[0])}
            else:
                answer = chat(ep, [{"role": "user", "content": "Reply with: ok"}], max_tokens=8, max_retries=0)
                report[kind] = {"ok": True, "model": answer.model, "reply": answer.text[:40]}
        except (ProviderError, ConfigError) as exc:
            report[kind] = {"ok": False, "error": str(exc)}
    report["ok"] = all(report[k]["ok"] for k in ("embedding", "llm"))
    return report


test_connection.__test__ = False  # not a pytest test
