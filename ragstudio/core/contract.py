"""The contract every RAG technique obeys.

A technique is a module exposing:

    SPEC = TechniqueSpec(...)
    def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult

The technique never opens a connection, reads configuration or picks a model: everything it may use arrives in
`deps`, already instrumented (timing, token usage, evidence). The core never imports a technique by name; the
registry discovers modules.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any, Protocol

from .errors import ValidationError
from .models import Answer, Context, Query, RetrievedChunk, StageTiming, Usage

STATUSES = ("implemented", "prototype", "adapter", "mock", "pending")
# Where a technique acts in the pipeline. It groups the catalog; it is not a timing stage (see `REQUIRED_STAGES`).
PIPELINE_STAGES = ("indexing", "query", "retrieval", "post_retrieval", "orchestration")
# Run settings a technique may replace with its own. The first two are grid axes: the runbook collapses them.
IGNORABLE = ("retrieval_mode", "reranker", "max_context_chars")
REQUIRED_STAGES = ("retrieval", "generation")


@dataclass(frozen=True)
class Param:
    default: Any
    help: str = ""
    choices: tuple[Any, ...] | None = None


@dataclass(frozen=True)
class TechniqueSpec:
    name: str
    version: str
    family: str
    description: str
    params: dict[str, Param] = field(default_factory=dict)
    requires: tuple[str, ...] = ("embedder", "llm")  # embedder | llm | reranker | index:<feature>
    reference: str = ""
    status: str = "implemented"
    origin: str = ""
    title: str = ""  # display name ("Corrective RAG"); `name` stays the stable identifier stored with every run
    stage: str = "retrieval"  # one of PIPELINE_STAGES
    # Run settings this technique replaces with its own (see IGNORABLE): a tuple, or a function of the resolved
    # parameters when it depends on them. Varying an ignored grid axis would only repeat the same run.
    ignores: tuple[str, ...] | Callable[[dict[str, Any]], tuple[str, ...]] = ()

    @property
    def label(self) -> str:
        return self.title or self.name

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValidationError(f"technique '{self.name}': status must be one of {STATUSES}")
        if self.stage not in PIPELINE_STAGES:
            raise ValidationError(f"technique '{self.name}': stage must be one of {PIPELINE_STAGES}")
        unknown = sorted(set(self.ignored_axes()) - set(IGNORABLE))
        if unknown:
            raise ValidationError(f"technique '{self.name}': cannot ignore {unknown}; allowed: {IGNORABLE}")

    def ignored_axes(self, params: dict[str, Any] | None = None) -> tuple[str, ...]:
        """Run settings ignored with these parameters (defaults when omitted), in IGNORABLE order."""
        found = self.ignores(self.resolve(params)) if callable(self.ignores) else self.ignores
        return tuple(axis for axis in IGNORABLE if axis in found) + tuple(a for a in found if a not in IGNORABLE)

    def resolve(self, params: dict[str, Any] | None) -> dict[str, Any]:
        """Defaults + given values; unknown names and invalid choices are rejected."""
        given = dict(params or {})
        unknown = sorted(set(given) - set(self.params))
        if unknown:
            raise ValidationError(f"technique '{self.name}': unknown parameter(s) {unknown}; "
                                  f"accepted: {sorted(self.params)}")
        resolved: dict[str, Any] = {}
        for name, spec in self.params.items():
            value = given.get(name, spec.default)
            if spec.default is not None and value is not None and not isinstance(spec.default, bool):
                if isinstance(spec.default, int) and not isinstance(value, bool):
                    value = int(value)
                elif isinstance(spec.default, float):
                    value = float(value)
            if spec.choices and value not in spec.choices:
                raise ValidationError(f"technique '{self.name}': {name}={value!r} not in {list(spec.choices)}")
            resolved[name] = value
        return resolved

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "title": self.label, "version": self.version, "family": self.family,
                "stage": self.stage, "ignores": list(self.ignored_axes()), "description": self.description,
                "params": {k: {"default": p.default, "help": p.help, "choices": list(p.choices) if p.choices else None}
                           for k, p in self.params.items()},
                "requires": list(self.requires), "reference": self.reference, "status": self.status,
                "origin": self.origin}


@dataclass(frozen=True)
class TechniqueRequest:
    query: Query
    k: int = 5
    max_context_chars: int = 6000
    params: dict[str, Any] = field(default_factory=dict)
    filters: dict[str, Any] | None = None


@dataclass(frozen=True)
class TechniqueResult:
    answer: Answer
    contexts: tuple[RetrievedChunk, ...]
    context: Context
    citations: tuple[dict[str, Any], ...]
    diagnostics: dict[str, Any]
    timings: tuple[StageTiming, ...]
    usage: Usage
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"answer": self.answer.to_dict(), "contexts": [c.to_dict() for c in self.contexts],
                "context": self.context.to_dict(), "citations": list(self.citations),
                "diagnostics": self.diagnostics, "timings": [t.to_dict() for t in self.timings],
                "usage": self.usage.to_dict(), "warnings": list(self.warnings)}


class AskFn(Protocol):
    def __call__(self, task: str, **variables: Any) -> str: ...


@dataclass(frozen=True)
class Tool:
    """A function the model may call (JSON Schema `parameters`, as in the OpenAI tools API)."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})

    def schema(self) -> dict[str, Any]:
        return {"type": "function", "function": {"name": self.name, "description": self.description,
                                                 "parameters": self.parameters}}


@dataclass(frozen=True)
class ToolCall:
    """What the model chose. `name` is empty when it answered in plain text instead of calling a tool."""
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    text: str = ""


class AskToolFn(Protocol):
    def __call__(self, task: str, tools: list[Tool], **variables: Any) -> ToolCall: ...


class RetrieveFn(Protocol):
    def __call__(self, query: str, k: int, *, mode: str | None = None, query_vector: list[float] | None = None,
                 filters: dict[str, Any] | None = None, **options: Any) -> list[RetrievedChunk]: ...


@dataclass
class TechniqueDeps:
    """Everything a technique may touch. Built by `ragstudio.experiments.deps.build_deps`.

    ask(task, **variables)   render the versioned prompt `task` and call the LLM (usage and evidence recorded)
    ask_tool(task, tools, **variables)  same, offering `tools` through native tool calling; returns a ToolCall
    log_retrieval(query, mode, items)   evidence for a ranking the technique computed itself (graph, tree...)
    embed(texts)             embedding vectors (usage recorded)
    retrieve(query, k, ...)  search the run's index; `mode` defaults to the run's retrieval mode
    rerank(query, chunks, k) the run's reranker (plain score sort + cut when the run has none)
    stage(name)              context manager that attributes wall-clock time to a pipeline stage
    usage()                  token/call totals so far
    store                    the IndexStore (chunk and document lookups, auxiliary structures)
    """
    ask: AskFn
    embed: Callable[[list[str]], list[list[float]]]
    retrieve: RetrieveFn
    rerank: Callable[[str, list[RetrievedChunk], int], list[RetrievedChunk]]
    stage: Callable[[str], AbstractContextManager[None]]
    timings: Callable[[], list[StageTiming]]
    usage: Callable[[], Usage]
    store: Any
    language: str = "pt"
    seed: int = 42
    has_reranker: bool = False
    llm_model: str = ""
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("ragstudio.technique"))
    ask_tool: AskToolFn | None = None
    log_retrieval: Callable[[str, str, list[RetrievedChunk]], None] = lambda query, mode, items: None


class TechniqueFn(Protocol):
    def __call__(self, request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult: ...


def validate_result(result: Any, spec: TechniqueSpec) -> TechniqueResult:
    """Structural check applied by the runner to every result, so all techniques stay comparable."""
    name = spec.name
    if not isinstance(result, TechniqueResult):
        raise ValidationError(f"technique '{name}' must return TechniqueResult, got {type(result).__name__}")
    if not isinstance(result.answer, Answer) or not isinstance(result.answer.text, str):
        raise ValidationError(f"technique '{name}': answer must be an Answer with text")
    if not isinstance(result.context, Context):
        raise ValidationError(f"technique '{name}': context must be a Context")
    if any(not isinstance(c, RetrievedChunk) for c in result.contexts):
        raise ValidationError(f"technique '{name}': contexts must be RetrievedChunk items")
    ids = {c.chunk.id for c in result.contexts}
    for cit in result.citations:
        if cit.get("chunk_id") not in ids:
            raise ValidationError(f"technique '{name}': citation {cit.get('chunk_id')!r} is not in contexts")
    missing_ctx = [cid for cid in result.context.chunk_ids if cid not in ids]
    if missing_ctx:
        raise ValidationError(f"technique '{name}': context references chunks not in contexts: {missing_ctx}")
    stages = {t.stage for t in result.timings}
    missing = [s for s in REQUIRED_STAGES if s not in stages]
    if missing:
        raise ValidationError(f"technique '{name}': timings must cover stages {missing}")
    if not isinstance(result.usage, Usage):
        raise ValidationError(f"technique '{name}': usage must be a Usage")
    if result.diagnostics.get("technique") != name:
        raise ValidationError(f"technique '{name}': diagnostics['technique'] must be '{name}'")
    try:
        json.dumps(result.diagnostics, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"technique '{name}': diagnostics is not JSON serializable ({exc})") from exc
    return result
