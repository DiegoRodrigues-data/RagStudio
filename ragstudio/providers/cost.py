"""Cost estimation from token counts. Local providers cost 0; unknown paid models yield None plus a warning."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PRICING_FILE = Path(__file__).with_name("pricing.json")


@lru_cache(maxsize=1)
def pricing() -> dict[str, Any]:
    return json.loads(PRICING_FILE.read_text(encoding="utf-8"))


def llm_cost(model: str, prompt_tokens: int, completion_tokens: int, local: bool = False) -> float | None:
    if local:
        return 0.0
    price = pricing()["llm"].get(model)
    if price is None:
        return None
    return (prompt_tokens * price["input"] + completion_tokens * price["output"]) / 1_000_000


def embedding_cost(model: str, tokens: int, local: bool = False) -> float | None:
    if local:
        return 0.0
    price = pricing()["embedding"].get(model)
    if price is None:
        return None
    return tokens * price["input"] / 1_000_000


def total_cost(*parts: float | None) -> float | None:
    """None when any part is unknown: a partial sum would look like a real (and wrong) number."""
    if any(p is None for p in parts):
        return None
    return round(sum(p for p in parts if p is not None), 8)
