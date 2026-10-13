"""Structured logging to stderr (stdout is reserved for the CLI JSON contract)."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {"ts": round(time.time(), 3), "level": record.levelname, "logger": record.name,
                                   "msg": record.getMessage()}
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def get_logger(name: str = "ragstudio") -> logging.Logger:
    root = logging.getLogger("ragstudio")
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
        root.setLevel(os.environ.get("RAGSTUDIO_LOG_LEVEL", "WARNING").upper())
        root.propagate = False
    return logging.getLogger(name)


def log(logger: logging.Logger, level: str, msg: str, **fields: Any) -> None:
    logger.log(getattr(logging, level.upper(), logging.INFO), msg, extra={"fields": fields})
