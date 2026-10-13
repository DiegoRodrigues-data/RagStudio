"""Canonical JSON and SHA-256. The same canonical form is used to hash and to verify (evidence chain rule)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def short_id(prefix: str, *parts: Any, length: int = 12) -> str:
    """Deterministic id such as `doc_3fa9c1d2e4b7` built from the given parts."""
    return f"{prefix}_{sha256_json(list(parts))[:length]}"
