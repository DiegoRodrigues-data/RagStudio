"""The plain-HTTP client and a whole runbook against a local OpenAI-compatible fake server (no network)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ragstudio.config.loader import load
from ragstudio.core.contract import Tool
from ragstudio.core.errors import ProviderError
from ragstudio.experiments import runbook
from ragstudio.experiments.runner import Runner
from ragstudio.providers import mock, openai_compat, routing


class FakeOpenAI(BaseHTTPRequestHandler):
    requests: list = []
    fail_next: list = []

    def log_message(self, *args):
        pass

    def _send(self, status, body, headers=None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self._send(200, {"data": [{"id": "fake-llm"}, {"id": "fake-embed"}]})

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append((self.path, payload, self.headers.get("Authorization")))
        if type(self).fail_next:
            status = type(self).fail_next.pop(0)
            return self._send(status, {"error": {"message": f"forced {status}"}}, {"Retry-After": "0"})
        if self.path.endswith("/embeddings"):
            vectors = mock.mock_embed(payload["input"], 32)
            return self._send(200, {"model": payload["model"], "usage": {"prompt_tokens": 7 * len(vectors)},
                                    "data": [{"index": i, "embedding": v} for i, v in enumerate(vectors)]})
        if payload.get("tools"):  # native tool calling: always pick the first tool offered
            name = payload["tools"][0]["function"]["name"]
            call = {"id": "t1", "type": "function", "function": {"name": name, "arguments": '{"query": "betz"}'}}
            return self._send(200, {"id": "c2", "model": "fake-llm-2026",
                                    "choices": [{"message": {"content": None, "tool_calls": [call]},
                                                 "finish_reason": "tool_calls"}],
                                    "usage": {"prompt_tokens": 50, "completion_tokens": 9}})
        user = payload["messages"][-1]["content"]
        text = "Resposta do servidor falso sobre " + user.split("Pergunta:")[-1].strip()[:40] + " [1]"
        self._send(200, {"id": "c1", "model": "fake-llm-2026", "system_fingerprint": "fp_test",
                         "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 111, "completion_tokens": 22}})


@pytest.fixture
def server(monkeypatch):
    FakeOpenAI.requests, FakeOpenAI.fail_next = [], []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    monkeypatch.delenv("RAGSTUDIO_PROVIDER")
    monkeypatch.setenv("RAGSTUDIO_LM_STUDIO_BASE_URL", f"http://127.0.0.1:{httpd.server_port}")
    monkeypatch.setenv("RAGSTUDIO_LLM_MODEL", "fake-llm")
    monkeypatch.setenv("RAGSTUDIO_EMBEDDING_MODEL", "fake-embed")
    monkeypatch.setattr(routing, "_sleep", lambda seconds: None)
    yield FakeOpenAI
    httpd.shutdown()


def test_chat_embed_and_models_over_http(server):
    cfg = load()
    assert cfg.provider() == "lmstudio"
    llm, emb = routing.resolve_endpoint("llm", cfg=cfg), routing.resolve_endpoint("embedding", cfg=cfg)
    out = routing.chat(llm, [{"role": "user", "content": "Pergunta: oi"}], temperature=0.0, max_tokens=64, seed=7)
    assert out.text.startswith("Resposta do servidor falso") and (out.prompt_tokens, out.completion_tokens) == (111, 22)
    assert out.usage_reported and out.system_fingerprint == "fp_test" and out.model == "fake-llm-2026"
    path, payload, auth = server.requests[-1]
    assert path == "/v1/chat/completions" and payload["seed"] == 7 and payload["temperature"] == 0.0 and auth is None
    vectors = routing.embed(emb, ["a b", "c d", "e f"], batch_size=2)
    assert len(vectors.vectors) == 3 and len(vectors.vectors[0]) == 32 and vectors.tokens == 21
    assert [len(p["input"]) for path, p, _ in server.requests if path.endswith("/embeddings")] == [2, 1]
    assert routing.list_models(cfg)["models"] == ["fake-embed", "fake-llm"]
    assert routing.test_connection(cfg)["ok"]


def test_native_tool_calling_over_http(server):
    llm = routing.resolve_endpoint("llm", cfg=load())
    tools = [Tool("search", "Search the documents.", {"type": "object", "properties": {"query": {"type": "string"}}})]
    out = routing.chat(llm, [{"role": "user", "content": "oi"}], tools=[t.schema() for t in tools])
    assert out.tool_calls == ({"name": "search", "arguments": {"query": "betz"}},) and out.text == ""
    assert out.finish_reason == "tool_calls" and out.completion_tokens == 9
    payload = server.requests[-1][1]
    assert payload["tool_choice"] == "auto" and payload["tools"][0]["function"]["name"] == "search"
    assert "tools" not in routing.chat(llm, [{"role": "user", "content": "Pergunta: oi"}]).raw
    broken = {"tool_calls": [{"function": {"name": "search", "arguments": "{not json"}}, {"function": {}}]}
    assert openai_compat.parse_tool_calls(broken) == ({"name": "search", "arguments": {}},)


def test_http_errors_retry_then_surface(server):
    llm = routing.resolve_endpoint("llm")
    server.fail_next.extend([429, 503])
    assert routing.chat(llm, [{"role": "user", "content": "x"}]).text
    server.fail_next.extend([400])
    with pytest.raises(ProviderError, match="HTTP 400: forced 400") as info:
        routing.chat(llm, [{"role": "user", "content": "x"}])
    assert info.value.status_code == 400 and not info.value.retryable
    dead = type(llm)(provider="lmstudio", model="m", base_url="http://127.0.0.1:9/v1")
    with pytest.raises(ProviderError, match="cannot reach lmstudio"):
        openai_compat.chat(dead, [{"role": "user", "content": "x"}], temperature=0, max_tokens=5, seed=None, timeout=2)


def test_runbook_against_http_provider(server, populated):
    repo = populated["repo"]
    created = runbook.create(repo, {"name": "http", "corpus": "energia", "question_set": "energia-perguntas",
                                    "techniques": ["naive", "hyde"], "chunking": {"size": 300, "overlap": 50},
                                    "k": 3, "limit_questions": 3}, load())
    summary = Runner(repo).execute_runbook(created["id"])
    assert summary["status"] == "completed" and summary["completed"] == 2
    run = repo.list_runs(created["id"])[0]
    assert run["config"]["llm"] == "fake-llm" and run["config"]["provider"] == "lmstudio" and run["cost_usd"] == 0.0
    result = repo.query_results(run["id"])[0]
    assert result["answer"].startswith("Resposta do servidor falso") and result["prompt_tokens"] == 111
    assert result["usage"]["estimated"] is False
    snapshot = repo.get_snapshot(run["id"])
    assert snapshot["llm"]["provider"] == "lmstudio" and snapshot["embedder"]["model"] == "fake-embed"
    response = next(e for e in repo.evidence(run["id"]) if e["kind"] == "response")
    assert response["payload"]["system_fingerprint"] == "fp_test" and response["payload"]["model"] == "fake-llm-2026"
    assert repo.get_index(run["index_hash"])["dim"] == 32
