"""Agentic RAG: the model plans, then chooses search tools step by step until it has enough to answer.

Related work: Singh et al., "Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG" (2025).

1. Planning: the LLM writes a short plan for the question (`planning`).
2. Acting: at each step it sees the question, the plan and numbered notes of the passages found so far, and picks
   one tool:
   - `search(query)`: the run's retrieval mode;
   - `keyword_search(query)`: exact-term BM25 search, for names, numbers and codes;
   - `read_more(passage)`: the chunks right before and after a passage already in the notes;
   - `finish()`: the notes are enough.
   Tools are offered through the provider's native tool calling (`tool_mode="native"`). When the provider rejects
   tools, or with `tool_mode="text"`, the same choice is requested as one JSON line.
3. Answering: the passages gathered go through the run's selection and the usual grounded answer.

The loop is bounded by `max_steps`; the whole trace is kept in `diagnostics["trace"]`. This is a single agent:
multi-agent orchestration and tools outside the index (web, SQL, calculators) are out of scope.
"""
from __future__ import annotations

import json
import re
from typing import Any

from ...core.contract import Param, TechniqueDeps, TechniqueRequest, TechniqueResult, TechniqueSpec, Tool, ToolCall
from ...core.errors import ProviderError
from ...core.models import RetrievedChunk
from ...core.pipeline import finish, generate, merge_pool, parse_lines, select

SPEC = TechniqueSpec(
    name="agentic", title="Agentic RAG", stage="orchestration", version="1.0.0", family="agent",
    description="The LLM plans, then picks search tools step by step (native tool calling) until it can answer.",
    params={"max_steps": Param(4, "maximum tool decisions"),
            "planning": Param(True, "write a plan before acting (one extra LLM call)"),
            "plan_steps": Param(3, "maximum steps of the plan"),
            "tool_mode": Param("native", "native: provider tool calling; text: one JSON line", ("native", "text")),
            "note_chars": Param(300, "characters of each passage shown to the agent as a note")},
    reference="https://arxiv.org/abs/2501.09136", origin="new",
)
_QUERY = {"type": "object", "properties": {"query": {"type": "string", "description": "what to look for"}},
          "required": ["query"]}
TOOLS = [
    Tool("search", "Search the document base by meaning. Use it for questions and descriptions.", _QUERY),
    Tool("keyword_search", "Search the document base for exact terms: names, numbers, codes, dates.", _QUERY),
    Tool("read_more", "Read the text right before and after a passage already in the notes.",
         {"type": "object", "properties": {"passage": {"type": "integer", "description": "number of the note"}},
          "required": ["passage"]}),
    Tool("finish", "Stop searching: the notes are enough to answer the question."),
]
_JSON = re.compile(r"\{.*\}", re.S)


def parse_text_choice(raw: str) -> ToolCall:
    match = _JSON.search(raw)
    try:
        data = json.loads(match.group(0)) if match else {}
    except ValueError:
        data = {}
    name = str(data.get("tool") or "") if isinstance(data, dict) else ""
    arguments = data.get("arguments") if isinstance(data, dict) and isinstance(data.get("arguments"), dict) else {}
    return ToolCall(name if name in {t.name for t in TOOLS} else "", arguments, raw)


def neighbours(deps: TechniqueDeps, item: RetrievedChunk) -> list[RetrievedChunk]:
    """The chunks right before and after `item` in its document, scored just below it."""
    ids = [f"{item.chunk.document_id}:{item.chunk.index + step}" for step in (-1, 1) if item.chunk.index + step >= 0]
    return [RetrievedChunk(chunk, item.score * 0.99, 0, "agentic:read_more") for chunk in deps.store.get(ids)]


def run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult:
    params = SPEC.resolve(request.params)
    question, k = request.query.text, request.k
    warnings: list[str] = []
    native = params["tool_mode"] == "native" and deps.ask_tool is not None
    plan: list[str] = []
    if params["planning"]:
        with deps.stage("control"):
            plan = parse_lines(deps.ask("agent_plan", query=question, n=params["plan_steps"]), params["plan_steps"])
    pool: list[RetrievedChunk] = []
    noted: list[RetrievedChunk] = []
    trace: list[dict[str, Any]] = []
    for step in range(1, max(1, params["max_steps"]) + 1):
        variables = {"query": question, "plan": "\n".join(f"- {p}" for p in plan) or "-", "step": step,
                     "max_steps": params["max_steps"],
                     "notes": "\n".join(f"[{n}] {c.chunk.text[:params['note_chars']].strip()}"
                                        for n, c in enumerate(noted, 1)) or "-"}
        with deps.stage("control"):
            choice = None
            if native:
                try:
                    choice = deps.ask_tool("agent_step", TOOLS, **variables)
                except ProviderError as exc:
                    if exc.retryable:
                        raise
                    native = False
                    warnings.append(f"the provider rejected native tool calling ({str(exc)[:80]}); "
                                    "the text protocol was used instead")
            if choice is None:
                described = "\n".join(f"- {t.name}: {t.description}" for t in TOOLS)
                choice = parse_text_choice(deps.ask("agent_step_text", tools=described, **variables))
        if choice.name in ("", "finish"):
            trace.append({"step": step, "action": "finish" if choice.name else "no_tool", "raw": choice.text[:80]})
            break
        found: list[RetrievedChunk] = []
        detail: dict[str, Any] = {}
        with deps.stage("retrieval"):
            if choice.name == "read_more":
                number = choice.arguments.get("passage")
                target = noted[int(number) - 1] if str(number).isdigit() and 0 < int(number) <= len(noted) else None
                found = neighbours(deps, target) if target else []
                detail = {"passage": number}
                deps.log_retrieval(f"read_more {number}", "agentic:read_more", found)
            else:
                query = str(choice.arguments.get("query") or "").strip() or question
                mode = "bm25" if choice.name == "keyword_search" else None
                found = deps.retrieve(query, k, mode=mode, filters=request.filters)
                detail = {"query": query}
        known = {c.chunk.id for c in pool}
        new = [c for c in found if c.chunk.id not in known]
        pool = merge_pool(pool, found)
        noted.extend(new)
        trace.append({"step": step, "action": choice.name, **detail, "new_chunks": len(new)})
    if not pool:
        warnings.append("the agent finished without searching; one search with the original question was forced")
        with deps.stage("retrieval"):
            pool = deps.retrieve(question, k, filters=request.filters)
        trace.append({"step": len(trace) + 1, "action": "forced_search", "query": question, "new_chunks": len(pool)})
    chunks = select(deps, question, pool, k)
    answer, context = generate(deps, question, chunks, request.max_context_chars)
    return finish(SPEC, deps, answer, chunks, context,
                  {"plan": plan, "tool_mode": "native" if native else "text", "steps": len(trace),
                   "tools_used": [t["action"] for t in trace], "pool": len(pool), "trace": trace}, warnings)
