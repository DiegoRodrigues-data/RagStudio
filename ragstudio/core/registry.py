"""Technique discovery. The core never imports a technique by name.

Sources, in order:
1. every module or package under `ragstudio.techniques` (packages expose their contract in `technique.py`);
2. every `*.py` file / package inside the directories listed in RAGSTUDIO_TECHNIQUES_PATH (os.pathsep separated),
   which lets a project add techniques without touching this repository.

Names starting with `_` are ignored.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import pkgutil
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from .contract import TechniqueFn, TechniqueSpec
from .errors import NotFoundError, ValidationError


@dataclass(frozen=True)
class Technique:
    spec: TechniqueSpec
    run: TechniqueFn
    module: str


_cache: dict[str, Technique] | None = None


def _register(found: dict[str, Technique], module: ModuleType) -> None:
    spec = getattr(module, "SPEC", None)
    run = getattr(module, "run", None)
    if spec is None and run is None:
        return  # helper module, not a technique
    if not isinstance(spec, TechniqueSpec) or not callable(run):
        raise ValidationError(f"{module.__name__}: a technique module must define SPEC (TechniqueSpec) and run()")
    if spec.name in found:
        raise ValidationError(f"duplicate technique name '{spec.name}' in {module.__name__} and "
                              f"{found[spec.name].module}")
    found[spec.name] = Technique(spec=spec, run=run, module=module.__name__)


def _discover_builtin(found: dict[str, Technique]) -> None:
    package = importlib.import_module("ragstudio.techniques")
    for info in pkgutil.iter_modules(package.__path__):
        if info.name.startswith("_"):
            continue
        target = f"ragstudio.techniques.{info.name}" + (".technique" if info.ispkg else "")
        _register(found, importlib.import_module(target))


def _load_path(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"cannot load technique module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _discover_external(found: dict[str, Technique]) -> None:
    for raw in filter(None, os.environ.get("RAGSTUDIO_TECHNIQUES_PATH", "").split(os.pathsep)):
        root = Path(raw)
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.name.startswith(("_", ".")):
                continue
            if entry.is_file() and entry.suffix == ".py":
                _register(found, _load_path(f"ragstudio_ext.{entry.stem}", entry))
            elif entry.is_dir() and (entry / "technique.py").is_file():
                _register(found, _load_path(f"ragstudio_ext.{entry.name}", entry / "technique.py"))


def reload() -> dict[str, Technique]:
    global _cache
    found: dict[str, Technique] = {}
    _discover_builtin(found)
    _discover_external(found)
    _cache = dict(sorted(found.items()))
    return _cache


def all_techniques() -> dict[str, Technique]:
    return _cache if _cache is not None else reload()


def get(name: str) -> Technique:
    techniques = all_techniques()
    if name not in techniques:
        raise NotFoundError(f"unknown technique '{name}'. Available: {', '.join(techniques) or '(none)'}")
    return techniques[name]


def title(name: str) -> str:
    """Display name of a technique ("Corrective RAG"); the identifier itself when it is not registered."""
    technique = all_techniques().get(name)
    return technique.spec.label if technique else name


def with_titles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copies of `rows` with `technique` replaced by its display name: for figures and report tables only.
    Exports keep the identifier, which is what joins them to the database."""
    return [{**row, "technique": title(str(row["technique"]))} if row.get("technique") else row for row in rows]


def list_specs() -> list[TechniqueSpec]:
    return [t.spec for t in all_techniques().values()]
