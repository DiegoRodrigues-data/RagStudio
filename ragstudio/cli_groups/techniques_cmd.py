"""`ragstudio techniques ...`: the catalog, straight from the registry."""
from __future__ import annotations

import argparse
from typing import Any

from ..core import registry
from .common import command


def _list(args: argparse.Namespace) -> Any:
    specs = [t.spec for t in registry.all_techniques().values()]
    if args.status:
        specs = [s for s in specs if s.status == args.status]
    return [{"name": s.name, "title": s.label, "version": s.version, "family": s.family, "stage": s.stage,
             "ignores": list(s.ignored_axes()), "requires": list(s.requires), "status": s.status,
             "description": s.description, "params": {k: p.default for k, p in s.params.items()},
             "reference": s.reference} for s in specs]


def _describe(args: argparse.Namespace) -> Any:
    technique = registry.get(args.name)
    return {**technique.spec.to_dict(), "module": technique.module}


def register(groups: Any) -> None:
    sub = groups.add_parser("techniques", help="catalog of RAG techniques").add_subparsers(dest="command",
                                                                                           required=True)
    command(sub, "list", _list, "registered techniques with status and default parameters").add_argument(
        "--status", choices=("implemented", "prototype", "adapter", "mock", "pending"))
    command(sub, "describe", _describe, "full specification of one technique").add_argument("--name", required=True)
