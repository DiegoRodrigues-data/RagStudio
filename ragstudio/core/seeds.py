"""Seed control: one integer drives `random`, numpy and the `seed` parameter sent to providers."""
from __future__ import annotations

import random

import numpy as np


def set_global_seed(seed: int) -> int:
    random.seed(seed)
    np.random.seed(seed % (2**32))
    return seed


def rng(seed: int) -> np.random.Generator:
    """Local generator: prefer it over the global state inside techniques."""
    return np.random.default_rng(seed)
