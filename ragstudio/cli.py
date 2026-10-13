"""RagStudio command line.

    ragstudio <group> <command> [--flag value ...]          (or: python -m ragstudio ...)

Contract: the LAST line of stdout is always one JSON object, `{"ok": true, "data": ...}` or
`{"ok": false, "error": "...", "error_type": "..."}`, plus `warnings` when there are any. Commands run with
`--stream` print `{"progress": {...}}` lines before it. Logs go to stderr. Exit code is 0 on success, 1 on a
handled error, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn

from . import __version__
from .cli_groups import GROUPS
from .cli_groups.common import take_warnings
from .core.errors import RagStudioError
from .core.logging import get_logger


class UsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise UsageError(f"{self.prog}: {message}")


def build_parser() -> Parser:
    parser = Parser(prog="ragstudio", description="Implement, run, compare and validate RAG techniques.")
    parser.add_argument("--version", action="version", version=f"ragstudio {__version__}")
    groups = parser.add_subparsers(dest="group", required=True, parser_class=Parser)
    for module in GROUPS:
        module.register(groups)
    return parser


def _print(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    logger = get_logger("ragstudio.cli")
    try:
        args = build_parser().parse_args(argv)
        data = args.func(args)
    except UsageError as exc:
        _print({"ok": False, "error": str(exc), "error_type": "UsageError"})
        return 2
    except RagStudioError as exc:
        _print({"ok": False, "error": str(exc), "error_type": type(exc).__name__, "warnings": take_warnings()})
        return 1
    except KeyboardInterrupt:
        _print({"ok": False, "error": "interrupted", "error_type": "KeyboardInterrupt"})
        return 1
    except Exception as exc:  # noqa: BLE001 - the contract must hold even for bugs
        logger.exception("unhandled error")
        _print({"ok": False, "error": f"{type(exc).__name__}: {exc}", "error_type": "InternalError",
                "warnings": take_warnings()})
        return 1
    payload: dict[str, Any] = {"ok": True, "data": data}
    warnings = take_warnings()
    if warnings:
        payload["warnings"] = warnings
    _print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
