"""Paired statistics for comparing two runs on the same questions. Dependency-free (numpy only).

paired_test() reports: mean difference, bootstrap confidence interval, paired t-test, Wilcoxon signed-rank
(normal approximation, flagged when n is small), sign-flip permutation test and Cohen's dz.
With few questions these tests have little power: always read the interval, not only the p-value.
"""
from __future__ import annotations

import math
from itertools import product
from typing import Any

import numpy as np


def _betacf(a: float, b: float, x: float) -> float:
    tiny, qab, qap, qam = 1e-30, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: int) -> float:
    return _betainc(df / 2.0, 0.5, df / (df + t * t)) if df > 0 else float("nan")


def normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def bootstrap_ci(diffs: np.ndarray, seed: int = 42, samples: int = 5000, level: float = 0.95) -> tuple[float, float]:
    generator = np.random.default_rng(seed)
    idx = generator.integers(0, len(diffs), size=(samples, len(diffs)))
    means = diffs[idx].mean(axis=1)
    low, high = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(low), float(high)


def permutation_p(diffs: np.ndarray, seed: int = 42, samples: int = 10000) -> float:
    """Two-sided sign-flip test on the mean difference: exact for n <= 12, Monte Carlo otherwise."""
    observed = abs(diffs.mean())
    if len(diffs) <= 12:
        signs = np.array(list(product((-1.0, 1.0), repeat=len(diffs))))
    else:
        signs = np.random.default_rng(seed).choice((-1.0, 1.0), size=(samples, len(diffs)))
    return float((np.abs((signs * diffs).mean(axis=1)) >= observed - 1e-12).mean())


def wilcoxon(diffs: np.ndarray) -> dict[str, Any]:
    nonzero = diffs[diffs != 0]
    n = len(nonzero)
    if n == 0:
        return {"statistic": 0.0, "p_value": 1.0, "n_nonzero": 0, "approximation": "none"}
    order = np.argsort(np.abs(nonzero), kind="mergesort")
    ranks = np.empty(n)
    sorted_abs = np.abs(nonzero)[order]
    i = 0
    while i < n:  # average ranks for ties
        j = i
        while j + 1 < n and sorted_abs[j + 1] == sorted_abs[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    w_plus = float(ranks[nonzero > 0].sum())
    mean, sd = n * (n + 1) / 4.0, math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    z = (w_plus - mean) / sd if sd else 0.0
    return {"statistic": w_plus, "p_value": normal_two_sided_p(z), "n_nonzero": n,
            "approximation": "normal" if n >= 10 else "normal (n < 10: unreliable, prefer the permutation test)"}


def paired_test(a: list[float], b: list[float], seed: int = 42) -> dict[str, Any]:
    """`a` and `b` are per-question values of the same metric, aligned by question. Difference = b - a."""
    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    n = len(a)
    if n < 2:
        return {"n": n, "note": "at least 2 paired observations are needed"}
    diffs = np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
    mean, sd = float(diffs.mean()), float(diffs.std(ddof=1))
    low, high = bootstrap_ci(diffs, seed)
    if sd == 0:
        t_stat, t_p = (0.0, 1.0) if mean == 0 else (math.copysign(math.inf, mean), 0.0)
    else:
        t_stat = mean / (sd / math.sqrt(n))
        t_p = t_two_sided_p(t_stat, n - 1)
    return {"n": n, "mean_a": round(float(np.mean(a)), 6), "mean_b": round(float(np.mean(b)), 6),
            "mean_diff": round(mean, 6), "ci95": [round(low, 6), round(high, 6)],
            "t": {"statistic": t_stat if math.isfinite(t_stat) else None, "p_value": round(t_p, 6), "df": n - 1},
            "wilcoxon": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in wilcoxon(diffs).items()},
            "permutation_p": round(permutation_p(diffs, seed), 6),
            "cohens_dz": round(mean / sd, 4) if sd else None}


def holm(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, in the original order."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = round(running, 6)
    return adjusted


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    rx, ry = _avg_rank(x), _avg_rank(y)
    return round(float(np.corrcoef(rx, ry)[0, 1]), 4)


def _avg_rank(values: list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty(len(arr))
    i = 0
    while i < len(arr):
        j = i
        while j + 1 < len(arr) and arr[order[j + 1]] == arr[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks
