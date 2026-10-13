"""Per-stage wall-clock timing shared by every technique."""
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from .models import StageTiming

# Canonical stage names, in pipeline order. A technique may use any subset; `retrieval` and `generation` are mandatory.
STAGES = ("query_transform", "retrieval", "rerank", "compression", "context", "generation", "control")


class StageTimer:
    def __init__(self) -> None:
        self._seconds: dict[str, float] = {}
        self._started = time.perf_counter()

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self._seconds[name] = self._seconds.get(name, 0.0) + (time.perf_counter() - start)

    def timings(self) -> list[StageTiming]:
        order = {name: i for i, name in enumerate(STAGES)}
        names = sorted(self._seconds, key=lambda n: (order.get(n, len(order)), n))
        return [StageTiming(stage=n, seconds=round(self._seconds[n], 6)) for n in names]

    def total(self) -> float:
        return round(time.perf_counter() - self._started, 6)
