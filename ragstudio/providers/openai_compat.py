"""Plain-HTTP client for OpenAI-compatible APIs (OpenAI, LM Studio 0.3+, Ollama /v1). No SDK dependency."""
from __future__ import annotations

import json
import time
from typing import Any

import requests

from ..core.errors import ProviderError
from .base import EmbedResult, Endpoint, LLMResult, estimate_tokens

REASONING_PREFIXES = ("o1", "o3", "o4", "gpt-5")


def is_reasoning_model(model: str) -> bool:
    return model.lower().startswith(REASONING_PREFIXES)


def _headers(ep: Endpoint) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if ep.api_key:
        headers["Authorization"] = f"Bearer {ep.api_key}"
    return headers


def post(ep: Endpoint, path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = ep.base_url.rstrip("/") + path
    try:
        response = requests.post(url, headers=_headers(ep), json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise ProviderError(f"cannot reach {ep.provider} at {url}: {exc}", status_code=503) from exc
    if response.status_code >= 400:
        retry_after = response.headers.get("Retry-After")
        try:
            detail = response.json().get("error", {})
            message = detail.get("message") if isinstance(detail, dict) else str(detail)
        except ValueError:
            message = response.text[:300]
        raise ProviderError(f"{ep.provider} returned HTTP {response.status_code}: {message}",
                            status_code=response.status_code,
                            retry_after=float(retry_after) if retry_after and retry_after.isdigit() else None)
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError(f"{ep.provider} returned a non-JSON body from {url}") from exc


def parse_tool_calls(message: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """`message.tool_calls` as [{"name", "arguments": dict}]; malformed argument JSON becomes {}."""
    calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        raw = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (ValueError, TypeError):
            arguments = {}
        if function.get("name"):
            calls.append({"name": str(function["name"]), "arguments": arguments if isinstance(arguments, dict) else {}})
    return tuple(calls)


def chat(ep: Endpoint, messages: list[dict[str, str]], *, temperature: float, max_tokens: int, seed: int | None,
         timeout: int, tools: list[dict[str, Any]] | None = None) -> LLMResult:
    payload: dict[str, Any] = {"model": ep.model, "messages": messages}
    if tools:
        payload.update({"tools": tools, "tool_choice": "auto"})
    if is_reasoning_model(ep.model):
        payload["max_completion_tokens"] = max_tokens  # reasoning models reject temperature/top_p/seed
    else:
        payload.update({"temperature": temperature, "max_tokens": max_tokens})
        if seed is not None:
            payload["seed"] = seed
    start = time.perf_counter()
    data = post(ep, "/chat/completions", payload, timeout)
    latency = time.perf_counter() - start
    try:
        choice = data["choices"][0]
        text = choice["message"].get("content") or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"{ep.provider} returned an unexpected chat payload") from exc
    usage = data.get("usage") or {}
    reported = "prompt_tokens" in usage
    prompt_tokens = int(usage.get("prompt_tokens") or estimate_tokens(" ".join(m["content"] for m in messages)))
    completion_tokens = int(usage.get("completion_tokens") or estimate_tokens(text))
    return LLMResult(text=text, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                     model=str(data.get("model") or ep.model), latency=latency, usage_reported=reported,
                     system_fingerprint=str(data.get("system_fingerprint") or ""),
                     finish_reason=str(choice.get("finish_reason") or ""),
                     raw={"id": data.get("id"), "usage": usage, "finish_reason": choice.get("finish_reason")},
                     tool_calls=parse_tool_calls(choice["message"]) if tools else ())


def embed(ep: Endpoint, texts: list[str], *, timeout: int) -> EmbedResult:
    start = time.perf_counter()
    data = post(ep, "/embeddings", {"model": ep.model, "input": texts}, timeout)
    latency = time.perf_counter() - start
    try:
        rows = sorted(data["data"], key=lambda row: row.get("index", 0))
        vectors = [list(map(float, row["embedding"])) for row in rows]
    except (KeyError, TypeError) as exc:
        raise ProviderError(f"{ep.provider} returned an unexpected embeddings payload") from exc
    if len(vectors) != len(texts):
        raise ProviderError(f"{ep.provider} returned {len(vectors)} embeddings for {len(texts)} inputs")
    usage = data.get("usage") or {}
    reported = "prompt_tokens" in usage or "total_tokens" in usage
    tokens = int(usage.get("prompt_tokens") or usage.get("total_tokens") or sum(estimate_tokens(t) for t in texts))
    return EmbedResult(vectors=vectors, tokens=tokens, model=str(data.get("model") or ep.model), latency=latency,
                       usage_reported=reported)


def list_models(ep: Endpoint, timeout: int = 10) -> list[str]:
    url = ep.base_url.rstrip("/") + "/models"
    try:
        response = requests.get(url, headers=_headers(ep), timeout=timeout)
        response.raise_for_status()
        return sorted(str(m.get("id")) for m in response.json().get("data", []) if m.get("id"))
    except (requests.RequestException, ValueError) as exc:
        raise ProviderError(f"cannot list models at {url}: {exc}", status_code=503) from exc
