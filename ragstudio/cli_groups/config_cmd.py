"""`ragstudio config ...`: show/set configuration, test the provider connection, list models."""
from __future__ import annotations

import argparse
from typing import Any

from ..config.loader import load
from ..core.errors import ValidationError
from ..providers import routing
from .common import command, json_value


def _show(args: argparse.Namespace) -> Any:
    return load().as_dict()


def _set(args: argparse.Namespace) -> Any:
    cfg = load()
    cfg.set(args.section, args.key, args.value)
    return {"saved": cfg.save(), "section": args.section, "key": args.key}


def _set_many(args: argparse.Namespace) -> Any:
    values = json_value(args.json, "--json")
    if not isinstance(values, dict) or not all(isinstance(v, dict) for v in values.values()):
        raise ValidationError('--json must be {"section": {"key": "value"}}')
    cfg = load()
    changed = 0
    for section, keys in values.items():
        for key, value in keys.items():
            cfg.set(section, key, "" if value is None else str(value))
            changed += 1
    return {"saved": cfg.save(), "changed": changed, "config": load().as_dict()}


def _test(args: argparse.Namespace) -> Any:
    return routing.test_connection()


def _models(args: argparse.Namespace) -> Any:
    return routing.list_models()


def register(groups: Any) -> None:
    sub = groups.add_parser("config", help="configuration and providers").add_subparsers(dest="command",
                                                                                         required=True)
    command(sub, "show", _show, "effective configuration (secrets masked)")
    p = command(sub, "set", _set, "write one value to config.local.ini")
    p.add_argument("--section", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--value", required=True)
    command(sub, "set-many", _set_many, "write several values at once").add_argument("--json", required=True)
    command(sub, "test-connection", _test, "one tiny embedding and chat call against the saved configuration")
    command(sub, "list-models", _models, "models offered by the configured provider")
