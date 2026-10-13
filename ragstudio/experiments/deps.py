"""Builds the instrumented `TechniqueDeps` handed to a technique for ONE question.

Every LLM call, embedding call and retrieval goes through here, which is what makes techniques comparable: the
same timing, token accounting and evidence trail regardless of how a technique combines the calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.contract import TechniqueDeps, Tool, ToolCall
from ..core.hashing import sha256_text
from ..core.logging import get_logger
from ..core.models import RetrievedChunk, Usage
from ..core.timing import StageTimer
from ..prompts import PromptSet
from ..providers import routing
from ..providers.base import Endpoint
from ..providers.cache import EmbeddingCache
from ..rerankers import build as build_reranker
from ..retrieval import retrieve as do_retrieve


@dataclass
class RunContext:
    """What is fixed for a whole run (one technique x one configuration)."""
    store: Any
    llm: Endpoint
    embedder: Endpoint
    prompts: PromptSet
    retrieval_mode: str = "dense"
    retrieval_options: dict[str, Any] = field(default_factory=dict)
    reranker: str = "none"
    reranker_options: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.0
    max_tokens: int = 1024
    seed: int = 42
    timeout_llm: int = 120
    timeout_embedding: int = 60
    max_retries: int = 4
    cache: EmbeddingCache | None = None


class Recorder:
    """Per-question accounting: usage totals plus the ordered list of evidence events."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.prompts: dict[str, dict[str, str]] = {}  # template sha -> {task, system, template}
        self.prompt_tokens = self.completion_tokens = self.llm_calls = 0
        self.embedding_calls = self.embedding_tokens = 0
        self.calls_by_task: dict[str, int] = {}
        self.estimated = False
        self.system_fingerprint = ""
        self.reported_model = ""

    def event(self, kind: str, **payload: Any) -> None:
        self.events.append({"kind": kind, "payload": payload})

    def usage(self) -> Usage:
        return Usage(prompt_tokens=self.prompt_tokens, completion_tokens=self.completion_tokens,
                     llm_calls=self.llm_calls, embedding_calls=self.embedding_calls,
                     embedding_tokens=self.embedding_tokens, calls_by_task=dict(self.calls_by_task),
                     estimated=self.estimated)


def build_deps(ctx: RunContext, recorder: Recorder | None = None) -> tuple[TechniqueDeps, Recorder]:
    rec = recorder or Recorder()
    timer = StageTimer()

    def call(task: str, variables: dict[str, Any], tools: list[Tool] | None = None) -> Any:
        prompt = ctx.prompts.render(task, **variables)
        rec.prompts[prompt.template_sha256] = {"task": task, "system": prompt.system,
                                               "template": ctx.prompts.template(task)}
        offered = {"tools": [t.name for t in tools]} if tools else {}
        rec.event("request", task=task, prompt_sha256=prompt.template_sha256, user=prompt.user,
                  model=ctx.llm.model, temperature=ctx.temperature, max_tokens=ctx.max_tokens, seed=ctx.seed,
                  **offered)
        result = routing.chat(
            ctx.llm, prompt.messages(), temperature=ctx.temperature, max_tokens=ctx.max_tokens, seed=ctx.seed,
            task=task, inputs=variables, timeout=ctx.timeout_llm, max_retries=ctx.max_retries,
            tools=[t.schema() for t in tools] if tools else None,
            on_retry=lambda attempt, exc: rec.event("retry", task=task, attempt=attempt, error=str(exc),
                                                    status_code=exc.status_code))
        rec.prompt_tokens += result.prompt_tokens
        rec.completion_tokens += result.completion_tokens
        rec.llm_calls += 1
        rec.calls_by_task[task] = rec.calls_by_task.get(task, 0) + 1
        rec.estimated = rec.estimated or not result.usage_reported
        rec.system_fingerprint = result.system_fingerprint or rec.system_fingerprint
        rec.reported_model = result.model or rec.reported_model
        rec.event("response", task=task, text=result.text, text_sha256=sha256_text(result.text),
                  prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens,
                  latency=round(result.latency, 6), model=result.model, finish_reason=result.finish_reason,
                  system_fingerprint=result.system_fingerprint, usage_reported=result.usage_reported,
                  **({"tool_calls": list(result.tool_calls)} if tools else {}))
        return result

    def ask(task: str, **variables: Any) -> str:
        return call(task, variables).text

    def ask_tool(task: str, tools: list[Tool], **variables: Any) -> ToolCall:
        result = call(task, variables, tools)
        known = {t.name for t in tools}
        chosen = next((c for c in result.tool_calls if c["name"] in known), None)
        if chosen is None:
            return ToolCall("", {}, result.text)
        return ToolCall(chosen["name"], dict(chosen["arguments"]), result.text)

    def log_retrieval(query: str, mode: str, items: list[RetrievedChunk]) -> None:
        rec.event("retrieval", query=query, mode=mode, k=len(items), options={}, filters=None,
                  results=[{"chunk_id": i.chunk.id, "score": round(float(i.score), 6), "rank": i.rank}
                           for i in items])

    def embed(texts: list[str]) -> list[list[float]]:
        result = routing.embed(ctx.embedder, texts, timeout=ctx.timeout_embedding, max_retries=ctx.max_retries,
                               cache=ctx.cache)
        rec.embedding_calls += 1
        rec.embedding_tokens += result.tokens
        rec.estimated = rec.estimated or not result.usage_reported
        return result.vectors

    def retrieve(query: str, k: int, *, mode: str | None = None, query_vector: list[float] | None = None,
                 filters: dict[str, Any] | None = None, **options: Any) -> list[RetrievedChunk]:
        used_mode = mode or ctx.retrieval_mode
        merged = {**ctx.retrieval_options, **options}
        items = do_retrieve(ctx.store, lambda q: embed([q])[0], query, k, mode=used_mode,
                            query_vector=query_vector, filters=filters, **merged)
        rec.event("retrieval", query=query, mode=used_mode, k=k, options=merged, filters=filters,
                  results=[{"chunk_id": i.chunk.id, "score": round(float(i.score), 6), "rank": i.rank}
                           for i in items])
        return items

    reranker = build_reranker(ctx.reranker, ask=ask, **ctx.reranker_options)

    def rerank(query: str, chunks: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
        if reranker is None:
            ordered = sorted(chunks, key=lambda c: (-c.score, c.chunk.id))[:k]
            return [c.with_rank(i) for i, c in enumerate(ordered, 1)]
        return reranker(query, chunks, k)

    deps = TechniqueDeps(ask=ask, embed=embed, retrieve=retrieve, rerank=rerank, stage=timer.stage,
                         timings=timer.timings, usage=rec.usage, store=ctx.store, language=ctx.prompts.language,
                         seed=ctx.seed, has_reranker=reranker is not None, llm_model=ctx.llm.model,
                         logger=get_logger("ragstudio.technique"), ask_tool=ask_tool, log_retrieval=log_retrieval)
    return deps, rec
