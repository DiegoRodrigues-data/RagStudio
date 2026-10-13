"""Shared CLI helpers. Handlers return plain data; `cli.main` wraps it in the JSON contract."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.errors import ValidationError

Handler = Callable[[argparse.Namespace], Any]
_warnings: list[str] = []


def warn(message: str) -> None:
    """Collected and returned in the final JSON line as `warnings`."""
    _warnings.append(message)


def take_warnings() -> list[str]:
    out = list(_warnings)
    _warnings.clear()
    return out


def progress_printer(enabled: bool) -> Callable[[dict[str, Any]], None] | None:
    """With --stream, every progress event is one JSON line on stdout before the final contract line."""
    if not enabled:
        return None

    def emit(event: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps({"progress": event}, ensure_ascii=False, default=str) + "\n")
        sys.stdout.flush()
    return emit


def json_value(raw: str | None, label: str = "value") -> Any:
    """Inline JSON, or `@path` to read JSON/YAML from a file."""
    if raw is None:
        return None
    if raw.startswith("@"):
        path = Path(raw[1:]).expanduser()
        if not path.is_file():
            raise ValidationError(f"{label}: file not found: {path}")
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".yaml", ".yml"):
            import yaml
            return yaml.safe_load(text)
        raw = text
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{label}: invalid JSON ({exc})") from exc


def command(sub: Any, name: str, handler: Handler, help_text: str) -> argparse.ArgumentParser:
    parser = sub.add_parser(name, help=help_text, description=help_text)
    parser.set_defaults(func=handler)
    return parser


def csv_list(raw: str | None) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]
