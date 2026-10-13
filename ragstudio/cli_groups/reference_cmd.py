"""`ragstudio reference ...`: the catalog of techniques, components, metrics, statistics and concepts."""
from __future__ import annotations

import argparse
from typing import Any

from .. import reference
from ..reference.entry import KINDS, LANGUAGES
from .common import command


def _list(args: argparse.Namespace) -> Any:
    return reference.catalog(args.language, args.kind)


def _show(args: argparse.Namespace) -> Any:
    return reference.show(args.id, args.language)


def register(groups: Any) -> None:
    sub = groups.add_parser("reference", help="what every technique, metric and concept means, with sources"
                            ).add_subparsers(dest="command", required=True)
    p = command(sub, "list", _list, "the whole catalog in one language")
    p.add_argument("--language", choices=LANGUAGES, default="pt")
    p.add_argument("--kind", choices=KINDS)
    p = command(sub, "show", _show, "one entry with its sources (ids as in `reference list`)")
    p.add_argument("--id", required=True)
    p.add_argument("--language", choices=LANGUAGES, default="pt")
