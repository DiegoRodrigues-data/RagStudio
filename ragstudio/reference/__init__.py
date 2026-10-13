"""Reference catalog: every technique, component, metric, statistic and concept the project uses, with its sources.

The catalog is data for the app's References page and for `ragstudio reference list`. Techniques are read live from
the registry (status, version, parameters, requirements) and joined with the prose in `techniques.py`; the other
kinds are static entries. Text exists in Portuguese and English; `catalog(language)` returns one of them.
"""
from __future__ import annotations

from typing import Any

from ..core import registry
from ..core.errors import NotFoundError, ValidationError
from . import components, concepts, guides, metrics, techniques
from .entry import KINDS, LANGUAGES, resolve
from .sources import SOURCES

GROUPS: dict[str, dict[str, str]] = {
    "running": {"pt": "Executando experimentos", "en": "Running experiments"},
    "reading": {"pt": "Interpretando resultados", "en": "Interpreting results"},
    "retrieval_mode": {"pt": "Modos de recuperação", "en": "Retrieval modes"},
    "reranker": {"pt": "Rerankers", "en": "Rerankers"},
    "chunking": {"pt": "Chunking", "en": "Chunking"},
    "store": {"pt": "Stores de índice", "en": "Index stores"},
    "indexing": {"pt": "Importação e indexação", "en": "Import and indexing"},
    "retrieval": {"pt": "Recuperação", "en": "Retrieval"},
    "generation_reference": {"pt": "Geração, com resposta esperada", "en": "Generation, reference based"},
    "generation_context": {"pt": "Geração, baseadas no contexto", "en": "Generation, context based"},
    "judge": {"pt": "Juiz e revisão humana", "en": "Judge and human review"},
    "efficiency": {"pt": "Eficiência", "en": "Efficiency"},
    "basics": {"pt": "Fundamentos", "en": "Basics"},
    "paired": {"pt": "Comparação pareada", "en": "Paired comparison"},
    "characteristics": {"pt": "Características dos documentos", "en": "Document characteristics"},
    "pipeline": {"pt": "Fluxo RAG", "en": "RAG flow"},
    "annotation": {"pt": "Perguntas e anotação", "en": "Questions and annotation"},
    "experiment": {"pt": "Experimento", "en": "Experiment"},
    "analysis": {"pt": "Avaliação e análise", "en": "Evaluation and analysis"},
}
STAGES: dict[str, dict[str, str]] = {
    "indexing": {"pt": "Documento e índice", "en": "Document and index"},
    "query": {"pt": "Consulta", "en": "Query"},
    "retrieval": {"pt": "Recuperação", "en": "Retrieval"},
    "post_retrieval": {"pt": "Pós-recuperação", "en": "Post-retrieval"},
    "orchestration": {"pt": "Orquestração", "en": "Orchestration"},
}
STATIC = (*guides.ENTRIES, *components.ENTRIES, *metrics.ENTRIES, *concepts.ENTRIES)


def _source_key(url: str) -> str | None:
    return next((key for key, source in SOURCES.items() if source["url"] == url), None)


def technique_entries() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """One raw entry per registered technique, plus ad hoc sources for reference URLs outside the bibliography."""
    entries: list[dict[str, Any]] = []
    extra: dict[str, dict[str, Any]] = {}
    order = list(STAGES)
    ranked = sorted(registry.all_techniques().values(), key=lambda t: (order.index(t.spec.stage), t.spec.name))
    for technique in ranked:
        spec = technique.spec
        prose = techniques.TEXT.get(spec.name, {})
        fallback = {"summary": spec.description}
        sources = list(prose.get("sources", ()))
        if spec.reference:
            key = _source_key(spec.reference)
            if key is None:
                key = f"technique:{spec.name}"
                extra[key] = {"authors": "", "year": None, "title": spec.reference, "venue": "", "url": spec.reference,
                              "checked": None}
            if key not in sources:
                sources.insert(0, key)
        entries.append({
            "id": f"technique.{spec.name}", "kind": "technique", "group": f"stage:{spec.stage}", "name": spec.label,
            "text": {"pt": prose.get("pt", fallback), "en": prose.get("en", fallback)},
            "facts": {"identifier": spec.name, "status": spec.status, "version": spec.version, "family": spec.family,
                      "stage": spec.stage, "ignores": list(spec.ignored_axes()),
                      "requires": list(spec.requires), "calls": prose.get("calls"),
                      "params": [{"name": name, "default": param.default, "help": param.help,
                                  "choices": list(param.choices) if param.choices else None}
                                 for name, param in spec.params.items()]},
            "sources": sources, "related": list(prose.get("related", ()))})
    return entries, extra


def raw_entries() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    technique_list, extra = technique_entries()
    by_kind = {kind: [e for e in (*STATIC, *technique_list) if e["kind"] == kind] for kind in KINDS}
    return [e for kind in KINDS for e in by_kind[kind]], {**SOURCES, **extra}


def catalog(language: str = "pt", kind: str | None = None) -> dict[str, Any]:
    """`{"language", "kinds", "groups", "entries", "sources"}`; entries in display order, grouped by `kind`."""
    if language not in LANGUAGES:
        raise ValidationError(f"unknown language '{language}' (available: {LANGUAGES})")
    if kind is not None and kind not in KINDS:
        raise ValidationError(f"unknown kind '{kind}' (available: {KINDS})")
    raw, sources = raw_entries()
    entries = [resolve(e, language) for e in raw if kind is None or e["kind"] == kind]
    groups = {key: label[language] for key, label in GROUPS.items()}
    groups.update({f"stage:{key}": label[language] for key, label in STAGES.items()})
    for item in entries:
        family = item["facts"].get("family")
        if family:
            groups[f"family:{family}"] = techniques.FAMILIES.get(family, {}).get(language, family)
    cited = {key for item in entries for key in item["sources"]}
    return {"language": language, "kinds": list(KINDS), "groups": groups, "entries": entries,
            "sources": {key: source for key, source in sources.items() if kind is None or key in cited}}


def show(entry_id: str, language: str = "pt") -> dict[str, Any]:
    data = catalog(language)
    found = next((e for e in data["entries"] if e["id"] == entry_id), None)
    if found is None:
        raise NotFoundError(f"reference entry '{entry_id}' not found")
    return {**found, "sources": [{"key": key, **data["sources"][key]} for key in found["sources"]]}
