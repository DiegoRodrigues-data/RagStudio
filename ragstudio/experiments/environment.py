"""Environment snapshot stored with every run: what an "Experimental Setup" section needs and nobody remembers."""
from __future__ import annotations

import platform
import subprocess
import sys
from importlib import metadata
from typing import Any

from .. import __version__
from ..core import paths

PACKAGES = ("numpy", "pandas", "requests", "pyyaml", "duckdb", "faiss-cpu", "chromadb", "pyarrow", "matplotlib", "jinja2", "docling",
            "sentence-transformers")


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.project_root(), capture_output=True, text=True,
                             timeout=5, check=False)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def package_versions() -> dict[str, str]:
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return versions


def snapshot(llm: dict[str, Any], embedder: dict[str, Any], seed: int) -> dict[str, Any]:
    return {"python_version": sys.version.split()[0], "platform": platform.platform(),
            "packages": package_versions(), "git_commit": git_commit(), "ragstudio_version": __version__,
            "llm": llm, "embedder": embedder, "seed": seed}
