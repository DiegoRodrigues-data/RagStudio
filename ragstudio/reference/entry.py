"""One catalog record. Text is written per language; `resolve` picks one and falls back to Portuguese."""
from __future__ import annotations

from typing import Any

LANGUAGES = ("pt", "en")
KINDS = ("guide", "technique", "component", "metric", "statistic", "concept")
SECTIONS = ("summary", "steps", "how", "read", "when", "cost", "limits")


def entry(id: str, kind: str, group: str, name: str | dict[str, str], *, pt: dict[str, str], en: dict[str, str],
          facts: dict[str, Any] | None = None, sources: tuple[str, ...] = (),
          related: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"id": id, "kind": kind, "group": group, "name": name, "text": {"pt": pt, "en": en},
            "facts": dict(facts or {}), "sources": list(sources), "related": list(related)}


def resolve(raw: dict[str, Any], language: str) -> dict[str, Any]:
    name = raw["name"] if isinstance(raw["name"], str) else raw["name"].get(language) or raw["name"]["pt"]
    text = raw["text"].get(language) or raw["text"]["pt"]
    return {"id": raw["id"], "kind": raw["kind"], "group": raw["group"], "name": name,
            "summary": text.get("summary", ""),
            "sections": [{"key": key, "text": text[key]} for key in SECTIONS if key != "summary" and text.get(key)],
            "facts": raw["facts"], "sources": raw["sources"], "related": raw["related"]}
