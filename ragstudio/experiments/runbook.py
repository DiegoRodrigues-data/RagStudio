"""Runbook: a grid of run configurations over techniques x indexing x models x parameters x seeds.

A runbook file (YAML or JSON) may give a scalar or a list for every axis; `expand()` produces one run per
combination, each with a canonical `config_hash` that identifies replicas across runbooks.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

from .. import rerankers as rerankers_mod
from .. import stores as stores_mod
from ..config.loader import Config
from ..core import registry
from ..core.errors import LeakageError, ValidationError
from ..core.hashing import sha256_json
from ..db.repository import Repo
from ..ingest.splits import select_questions
from ..processing.chunking import normalize_config
from ..providers import cost as pricing
from ..rerankers import NAMES as RERANKERS
from ..retrieval import MODES
from ..stores import KINDS as STORES

PRESETS: dict[str, dict[str, Any]] = {
    "quick": {"techniques": ["naive", "hyde", "multi_query"], "k": [4], "seeds": [42]},
    "comparative": {"techniques": ["naive", "hyde", "multi_query", "decomposition", "iterative",
                                   "context_compression", "mmr_rag", "rag_evo"],
                    "retrieval_modes": ["dense", "hybrid"], "k": [5], "seeds": [42]},
    "full": {"techniques": "all", "retrieval_modes": ["dense", "hybrid", "rrf"], "k": [3, 5, 8],
             "seeds": [42, 43, 44]},
}
AXES = ("chunking", "embedding_models", "llms", "k", "seeds", "retrieval_modes", "rerankers", "enrich")


def options() -> dict[str, list[dict[str, Any]]]:
    """Runbook choices that depend on optional packages, with the package to install when one is missing."""
    def rows(names: tuple[str, ...], missing: Any) -> list[dict[str, Any]]:
        return [{"name": n, "available": missing(n) is None, "requires": missing(n)} for n in names]
    return {"rerankers": rows(RERANKERS, rerankers_mod.missing_dependency),
            "stores": rows(STORES, stores_mod.missing_dependency)}


def load_file(path: str | Path) -> dict[str, Any]:
    file = Path(path).expanduser()
    if not file.is_file():
        raise ValidationError(f"runbook file not found: {file}")
    raw = file.read_text(encoding="utf-8")
    try:
        if file.suffix.lower() in (".yaml", ".yml"):
            import yaml
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001 - any parser error becomes a validation message
        raise ValidationError(f"cannot parse {file}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{file}: a runbook must be a mapping")
    return data


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _techniques(raw: Any) -> list[dict[str, Any]]:
    if raw == "all":
        raw = [spec.name for spec in registry.list_specs()]
    out = []
    for item in _as_list(raw):
        entry = {"name": item} if isinstance(item, str) else dict(item or {})
        if "name" not in entry:
            raise ValidationError("each technique entry needs a 'name'")
        spec = registry.get(entry["name"]).spec
        params, grid = dict(entry.get("params") or {}), dict(entry.get("grid") or {})
        overlap = sorted(set(params) & set(grid))
        if overlap:
            raise ValidationError(f"technique '{spec.name}': {overlap} given in both params and grid")
        for values in itertools.product(*[_as_list(v) for v in grid.values()]) if grid else [()]:
            combo = {**params, **dict(zip(grid.keys(), values, strict=True))}
            spec.resolve(combo)  # validates names, types and choices early
            out.append({"name": spec.name, "version": spec.version, "params": combo})
    if not out:
        raise ValidationError("a runbook needs at least one technique")
    return out


def normalize(raw: dict[str, Any], cfg: Config) -> dict[str, Any]:
    """Explicit configuration with every default filled in. Raises ValidationError on anything inconsistent."""
    data = {**PRESETS.get(str(raw.get("preset") or ""), {}), **{k: v for k, v in raw.items() if k != "preset"}}
    if raw.get("preset") and raw["preset"] not in PRESETS:
        raise ValidationError(f"unknown preset '{raw['preset']}' (available: {sorted(PRESETS)})")
    for required in ("name", "corpus", "question_set"):
        if not data.get(required):
            raise ValidationError(f"runbook is missing '{required}'")
    provider = cfg.provider()
    default_embedding = None if provider == "mock" else cfg.get("embedding", "model")
    default_llm = None if provider == "mock" else cfg.get("llm", "model")
    evaluation = dict(data.get("evaluation") or {})
    config: dict[str, Any] = {
        "name": str(data["name"]), "description": str(data.get("description") or ""),
        "corpus": str(data["corpus"]), "split": data.get("split"), "question_set": str(data["question_set"]),
        "techniques": _techniques(data.get("techniques") or ["naive"]),
        "chunking": [normalize_config(c) for c in _as_list(data.get("chunking") or {})],
        "embedding_models": _as_list(data.get("embedding_models") or data.get("embedding_model") or default_embedding),
        "llms": _as_list(data.get("llms") or data.get("llm") or default_llm),
        "k": [int(v) for v in _as_list(data["k"] if data.get("k") is not None
                                       else cfg.get_int("experiments", "k", 5))],
        "seeds": [int(v) for v in _as_list(next((data[key] for key in ("seeds", "seed") if data.get(key) is not None),
                                                cfg.get_int("experiments", "seed", 42)))],
        "retrieval_modes": _as_list(data.get("retrieval_modes") or data.get("retrieval_mode")
                                    or cfg.get("experiments", "retrieval_mode", "dense")),
        "rerankers": _as_list(data.get("rerankers") or data.get("reranker") or "none"),
        "enrich": _as_list(data.get("enrich")) if "enrich" in data else [None],
        "store": str(data.get("store") or cfg.get("experiments", "store", "memory")),
        "language": str(data.get("language") or cfg.get("experiments", "language", "pt")),
        "max_context_chars": int(data.get("max_context_chars")
                                 or cfg.get_int("experiments", "max_context_chars", 6000)),
        "temperature": float(data.get("temperature", cfg.get_float("llm", "temperature", 0.0))),
        "max_tokens": int(data.get("max_tokens") or cfg.get_int("llm", "max_tokens", 1024)),
        "retrieval_options": dict(data.get("retrieval_options") or {}),
        "evaluation": {"judge": bool(evaluation.get("judge", cfg.get_bool("evaluation", "judge"))),
                       "judge_model": evaluation.get("judge_model") or cfg.get("evaluation", "judge_model") or None},
        "max_budget_usd": float(data["max_budget_usd"]) if data.get("max_budget_usd") is not None else None,
        "limit_questions": int(data["limit_questions"]) if data.get("limit_questions") else None,
        "prune": bool(data.get("prune", True)),
        "provider": provider,
    }
    _check(config["retrieval_modes"], MODES, "retrieval mode")
    _check(config["rerankers"], RERANKERS, "reranker")
    _check([config["store"]], STORES, "store")
    _check(config["enrich"], (None, "contextual"), "enrichment")
    for name, package in [(r, rerankers_mod.missing_dependency(r)) for r in config["rerankers"]] + \
                         [(config["store"], stores_mod.missing_dependency(config["store"]))]:
        if package:
            raise ValidationError(f"'{name}' needs the `{package}` package, which is not installed "
                                  f"(pip install {package}); install it or remove '{name}' from the runbook")
    if config["store"] == "faiss" and "cross_encoder" in config["rerankers"]:
        # faiss-cpu and torch each ship their own OpenMP runtime; loading both aborts the process on macOS.
        raise ValidationError("store 'faiss' cannot be combined with the 'cross_encoder' reranker (FAISS and PyTorch "
                              "clash in one process); use another store or another reranker")
    if config["split"] not in (None, "train", "validation", "test"):
        raise ValidationError(f"unknown split '{config['split']}'")
    if any(v <= 0 for v in config["k"]):
        raise ValidationError("k must be positive")
    return config


def _check(values: list[Any], allowed: tuple[Any, ...], label: str) -> None:
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ValidationError(f"unknown {label}(s) {bad} (available: {[a for a in allowed if a is not None]})")


INDEX_REQUIREMENTS = {
    "index:parent_child": (lambda c: c["chunking"].get("strategy") == "parent_child",
                           "needs an index chunked with strategy parent_child"),
    "index:contextual": (lambda c: c["enrich"] == "contextual", "needs an index built with enrich: contextual"),
}
GRID_IGNORABLE = ("retrieval_mode", "reranker")


def expand_with_report(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One run per combination of the grid axes, in deterministic order, plus what pruning left out.

    With `prune` (the default) two kinds of combination are skipped:
    - redundant: the technique ignores a grid axis (`SPEC.ignores`), so varying it would repeat the same run. The
      first value of the axis is kept and the run records `ignored_axes`;
    - incompatible: the technique needs an index the combination does not build (`index:parent_child`,
      `index:contextual`); it would silently behave like `naive`.
    """
    shared = {key: config[key] for key in ("corpus", "split", "question_set", "store", "language",
                                           "max_context_chars", "temperature", "max_tokens", "retrieval_options",
                                           "evaluation", "limit_questions", "provider")}
    prune = config.get("prune", True)
    specs = {t["name"]: registry.get(t["name"]).spec for t in config["techniques"]}
    runs: list[dict[str, Any]] = []
    seen: set[str] = set()
    report: dict[str, dict[str, Any]] = {}
    total = 0
    for chunking, embedding, llm, k, seed, mode, reranker, enrich in itertools.product(
            *[config[axis] for axis in AXES]):
        for technique in config["techniques"]:
            total += 1
            spec = specs[technique["name"]]
            ignored = spec.ignored_axes(technique["params"])
            entry = report.setdefault(spec.name, {"technique": spec.name, "runs": 0, "redundant": 0,
                                                  "incompatible": 0, "ignores": [], "needs": []})
            entry["ignores"] = sorted(set(entry["ignores"]) | set(ignored))
            run_config = {**shared, "technique": technique["name"], "technique_version": technique["version"],
                          "params": technique["params"], "chunking": chunking, "embedding_model": embedding,
                          "llm": llm, "k": k, "seed": seed, "retrieval_mode": mode, "reranker": reranker,
                          "enrich": enrich}
            if ignored:
                run_config["ignored_axes"] = list(ignored)
            if prune:
                unmet = [reason for need, (ok, reason) in INDEX_REQUIREMENTS.items()
                         if need in spec.requires and not ok(run_config)]
                if unmet:
                    entry["incompatible"] += 1
                    entry["needs"] = sorted(set(entry["needs"]) | set(unmet))
                    continue
                effective = {**run_config, **{axis: None for axis in GRID_IGNORABLE if axis in ignored}}
                key = sha256_json(effective)
                if key in seen:
                    entry["redundant"] += 1
                    continue
                seen.add(key)
            entry["runs"] += 1
            runs.append({"technique": technique["name"], "technique_version": technique["version"],
                         "config": run_config, "config_hash": sha256_json(run_config)})
    by_technique = [e for e in report.values() if e["redundant"] or e["incompatible"]]
    return runs, {"enabled": prune, "full_grid": total, "runs": len(runs),
                  "redundant": sum(e["redundant"] for e in by_technique),
                  "incompatible": sum(e["incompatible"] for e in by_technique),
                  "without_runs": sorted(e["technique"] for e in report.values() if not e["runs"]),
                  "by_technique": sorted(by_technique, key=lambda e: e["technique"])}


def expand(config: dict[str, Any]) -> list[dict[str, Any]]:
    return expand_with_report(config)[0]


def _no_runs(pruned: dict[str, Any]) -> ValidationError:
    reasons = "; ".join(f"{e['technique']} {', '.join(e['needs'])}" for e in pruned["by_technique"] if e["needs"])
    return ValidationError(f"no run is left after pruning incompatible combinations ({reasons}); "
                           "adjust the grid or set prune: false")


def resolve_data(repo: Repo, config: dict[str, Any]) -> dict[str, Any]:
    """Corpus, documents and questions a run will use, after split filtering and the leakage check."""
    corpus = repo.get_corpus(config["corpus"])
    question_set = repo.get_question_set(config["question_set"])
    questions = repo.list_questions(question_set["id"])
    documents = repo.corpus_documents(corpus["id"])
    all_ids = {d.id for d in documents}
    split = config.get("split")
    if split:
        splits = repo.get_splits(corpus["id"])
        if split not in splits:
            raise LeakageError(f"corpus '{corpus['name']}' has no '{split}' split (run `corpus split` first)")
        split_ids = splits[split]
        documents = [d for d in documents if d.id in set(split_ids)]
        questions = select_questions(questions, split, split_ids)
    else:
        tagged = sorted({q["split"] for q in questions if q.get("split")})
        if tagged:
            raise LeakageError(f"question set '{question_set['name']}' has questions tagged with splits {tagged} "
                               f"but the runbook declares no split; set `split:` to avoid mixing them")
    unknown = sorted({g["document_id"] for q in questions for g in q["gold_passages"]} - all_ids)
    if unknown:
        raise ValidationError(f"gold passages reference documents that are not in corpus '{corpus['name']}': "
                              f"{unknown[:5]}")
    if config.get("limit_questions"):
        questions = questions[:config["limit_questions"]]
    if not questions:
        raise ValidationError("no questions left to ask after split filtering")
    if not documents:
        raise ValidationError("no documents left to index after split filtering")
    return {"corpus": corpus, "question_set": question_set, "questions": questions, "documents": documents}


def estimate(config: dict[str, Any], runs: list[dict[str, Any]], n_questions: int) -> dict[str, Any]:
    """Lower bound: one answer call per question per run. Multi-call techniques (hyde, multi_query, iterative,
    rag_evo, compression, agentic...) cost more; the real cost is measured and stored after execution."""
    total_prompt = total_completion = 0
    cost: float | None = 0.0
    for run in runs:
        c = run["config"]
        context_chars = min(c["max_context_chars"], c["k"] * int(c["chunking"]["size"]))
        prompt_tokens = (context_chars + 400) // 4 * n_questions
        completion_tokens = 150 * n_questions
        total_prompt += prompt_tokens
        total_completion += completion_tokens
        part = pricing.llm_cost(c["llm"] or "mock-llm", prompt_tokens, completion_tokens,
                                local=c["provider"] in ("mock", "lmstudio", "ollama"))
        cost = None if cost is None or part is None else cost + part
    return {"runs": len(runs), "questions_per_run": n_questions, "answers": len(runs) * n_questions,
            "lower_bound": True, "prompt_tokens": total_prompt, "completion_tokens": total_completion,
            "cost_usd": round(cost, 6) if cost is not None else None,
            "note": "lower bound assuming one LLM call per question; unknown model prices give cost_usd = null"}


def preview(repo: Repo, raw: dict[str, Any], cfg: Config) -> dict[str, Any]:
    config = normalize(raw, cfg)
    runs, pruned = expand_with_report(config)
    if not runs:
        raise _no_runs(pruned)
    data = resolve_data(repo, config)
    return {"config": config, "runs": len(runs), "estimate": estimate(config, runs, len(data["questions"])),
            "corpus": data["corpus"]["name"], "documents": len(data["documents"]),
            "questions": len(data["questions"]),
            "techniques": sorted({r["technique"] for r in runs}), "pruned": pruned,
            "duplicate_configs": len(runs) - len({r["config_hash"] for r in runs})}


def create(repo: Repo, raw: dict[str, Any], cfg: Config) -> dict[str, Any]:
    config = normalize(raw, cfg)
    runs, pruned = expand_with_report(config)
    if not runs:
        raise _no_runs(pruned)
    data = resolve_data(repo, config)
    est = estimate(config, runs, len(data["questions"]))
    if config["max_budget_usd"] is not None and est["cost_usd"] is not None \
            and est["cost_usd"] > config["max_budget_usd"]:
        raise ValidationError(f"estimated lower-bound cost ${est['cost_usd']:.4f} already exceeds the budget "
                              f"${config['max_budget_usd']:.4f}")
    runbook = repo.create_runbook(config["name"], config, runs, est, config["description"], config["max_budget_usd"])
    return {"id": runbook["id"], "name": runbook["name"], "runs": len(runs), "estimate": est, "pruned": pruned}
