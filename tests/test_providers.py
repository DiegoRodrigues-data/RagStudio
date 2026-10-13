import pytest

from ragstudio.config.loader import load
from ragstudio.core.errors import ConfigError, ProviderError
from ragstudio.providers import cost, mock, openai_compat, routing
from ragstudio.providers.base import Endpoint, LLMResult
from ragstudio.providers.cache import EmbeddingCache
from ragstudio.providers.lmstudio import normalize_local_base


def test_mock_embeddings_are_deterministic_and_similarity_aware():
    a, b = mock.mock_vector("turbina eólica vento"), mock.mock_vector("turbina eólica vento")
    assert a == b and len(a) == 96
    dot = lambda x, y: sum(i * j for i, j in zip(x, y, strict=True))  # noqa: E731
    near, far = mock.mock_vector("vento turbina aerogerador"), mock.mock_vector("usina hidrelétrica represa")
    assert dot(a, near) > dot(a, far)


def test_mock_chat_rules_are_deterministic():
    context = "[1] (d · chunk 0)\nO limite de Betz é de 59,3%. Outra frase.\n\n[2] (d · chunk 1)\nNada relevante."
    first = mock.mock_chat([], task="answer", inputs={"query": "Qual o limite de Betz?", "context": context})
    assert first == mock.mock_chat([], task="answer", inputs={"query": "Qual o limite de Betz?", "context": context})
    assert first == "O limite de Betz é de 59,3%. [1]"
    assert mock.mock_chat([], task="answer", inputs={"query": "x", "context": ""}) == mock.REFUSAL
    assert mock.mock_chat([], task="rerank", inputs={"query": "betz", "passages": ["nada", "limite de betz"]}) == "2,1"
    assert len(mock.mock_chat([], task="multi_queries", inputs={"query": "limite de Betz vento", "n": 3}).splitlines()) == 3


def test_routing_precedence(monkeypatch):
    monkeypatch.delenv("RAGSTUDIO_PROVIDER")
    cfg = load()
    assert cfg.provider() == "openai"
    with pytest.raises(ConfigError, match="OpenAI API key is not configured"):
        routing.resolve_endpoint("llm", cfg=cfg)
    cfg.set("ollama", "base_url", "http://localhost:11434")
    assert cfg.provider() == "ollama"
    cfg.set("lm_studio", "base_url", "http://localhost:1234/")
    assert cfg.provider() == "lmstudio"
    ep = routing.resolve_endpoint("embedding", cfg=cfg)
    assert (ep.provider, ep.base_url, ep.is_local) == ("lmstudio", "http://localhost:1234/v1", True)
    cfg.set("openai", "api_key", "sk-test-1234567890")
    cfg.set("openai", "models_allowlist", "gpt-4o-mini")
    assert routing.resolve_endpoint("llm", "gpt-4o-mini", cfg).provider == "openai"
    assert routing.resolve_endpoint("llm", "local-model", cfg).provider == "lmstudio"
    assert "sk-test-1234567890" not in str(cfg.as_dict()) and "api_key" not in ep.public()


def test_config_save_and_reload(isolated_env):
    cfg = load()
    cfg.set("llm", "model", "my-model")
    cfg.save()
    assert load().get("llm", "model") == "my-model"
    with pytest.raises(ConfigError, match="unknown configuration key"):
        cfg.set("llm", "nope", "1")


def test_normalize_local_base():
    assert normalize_local_base("http://h:1/") == "http://h:1/v1" == normalize_local_base("http://h:1/v1")


def test_chat_retries_on_429_then_succeeds(monkeypatch):
    calls, slept, retries = [], [], []

    def fake(ep, messages, **kw):
        calls.append(1)
        if len(calls) < 3:
            raise ProviderError("rate limited", status_code=429, retry_after=7)
        return LLMResult("ok", 1, 1, "m", 0.0)
    monkeypatch.setattr(openai_compat, "chat", fake)
    monkeypatch.setattr(routing, "_sleep", slept.append)
    out = routing.chat(Endpoint("openai", "m", "http://x", "k"), [{"role": "user", "content": "hi"}],
                       on_retry=lambda n, e: retries.append(n))
    assert out.text == "ok" and len(calls) == 3 and slept == [7, 7] and retries == [1, 2]


def test_chat_does_not_retry_client_errors(monkeypatch):
    def fake(ep, messages, **kw):
        raise ProviderError("bad request", status_code=400)
    monkeypatch.setattr(openai_compat, "chat", fake)
    monkeypatch.setattr(routing, "_sleep", lambda s: pytest.fail("must not sleep"))
    with pytest.raises(ProviderError, match="bad request"):
        routing.chat(Endpoint("openai", "m", "http://x", "k"), [{"role": "user", "content": "hi"}])


def test_reasoning_models_get_no_temperature(monkeypatch):
    sent = {}

    def fake_post(ep, path, payload, timeout):
        sent.update(payload)
        return {"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}], "model": "o3-mini"}
    monkeypatch.setattr(openai_compat, "post", fake_post)
    out = openai_compat.chat(Endpoint("openai", "o3-mini", "http://x", "k"), [{"role": "user", "content": "hi"}],
                             temperature=0.0, max_tokens=50, seed=1, timeout=5)
    assert "temperature" not in sent and "seed" not in sent and sent["max_completion_tokens"] == 50
    assert out.usage_reported is False and out.prompt_tokens >= 0


def test_cost_unknown_model_is_none_not_zero():
    assert cost.llm_cost("gpt-4o-mini", 1_000_000, 1_000_000) == pytest.approx(0.75)
    assert cost.llm_cost("some-unknown-model", 100, 100) is None
    assert cost.llm_cost("some-local-model", 100, 100, local=True) == 0.0
    assert cost.total_cost(0.1, None) is None and cost.total_cost(0.1, 0.2) == pytest.approx(0.3)


def test_embedding_cache_avoids_second_computation(isolated_env):
    ep = routing.resolve_endpoint("embedding")
    cache = EmbeddingCache()
    first = routing.embed(ep, ["um texto", "outro texto"], cache=cache)
    second = routing.embed(ep, ["um texto", "novo"], cache=cache)
    cache.close()
    assert first.cache_hits == 0 and second.cache_hits == 1
    assert second.vectors[0] == pytest.approx(first.vectors[0], abs=1e-6)


def test_connection_test_with_mock():
    report = routing.test_connection()
    assert report["ok"] and report["provider"] == "mock" and report["embedding"]["dim"] == 96
