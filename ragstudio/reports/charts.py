"""Figures built from the comparison tables. Each function returns {"png": path, "svg": path, "pdf": path} or
raises SkipFigure when there is nothing to draw.

Form choices: one metric across techniques is magnitude -> horizontal bars in a single hue, sorted, value labels.
Latency by stage is part-to-whole -> stacked bars, stage colors in a fixed order with a legend. Two measures are
never put on two y-axes: cost/latency vs quality is a scatter with direct labels.
"""
from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

from ..core.timing import STAGES
from . import style
from .style import SkipFigure


def _series(rows: list[dict[str, Any]], key: str, metric: str) -> list[tuple[str, float, int]]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        if row.get(metric) is not None:
            groups.setdefault(str(row.get(key)), []).append(float(row[metric]))
    return [(name, statistics.fmean(values), len(values)) for name, values in groups.items()]


def metric_bars(rows: list[dict[str, Any]], metric: str, directory: Path, key: str = "technique",
                name: str | None = None) -> dict[str, str]:
    data = sorted(_series(rows, key, metric), key=lambda item: item[1])
    if not data:
        raise SkipFigure(f"no values for {metric}")
    plt = style.pyplot()
    fig, ax = plt.subplots(figsize=(6.4, max(2.2, 0.36 * len(data) + 1.1)))
    labels, values = [d[0] for d in data], [d[1] for d in data]
    bars = ax.barh(labels, values, color=style.PRIMARY, height=0.62, edgecolor=style.SURFACE, linewidth=1.5)
    top = max(values) or 1.0
    for bar, value in zip(bars, values, strict=True):
        ax.text(value + top * 0.012, bar.get_y() + bar.get_height() / 2, f"{value:.3g}", va="center", ha="left",
                fontsize=8, color=style.TEXT)
    ax.set_xlim(0, top * 1.14)
    ax.set_xlabel(style.label(metric))
    ax.set_title(f"{style.label(metric)} by {key.replace('_', ' ')}", loc="left")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    return style.save(fig, directory, name or f"{metric}_by_{key}")


def latency_stages(rows: list[dict[str, Any]], directory: Path, key: str = "technique") -> dict[str, str]:
    stage_columns = sorted({c for row in rows for c in row if c.startswith("latency_")
                            and c not in ("latency_mean", "latency_median", "latency_total")
                            and row.get(c) is not None},
                           key=lambda c: (STAGES.index(c[8:]) if c[8:] in STAGES else len(STAGES), c))
    if not stage_columns:
        raise SkipFigure("no per-stage latency")
    if len(stage_columns) > style.MAX_SERIES:
        raise SkipFigure("too many stages to color distinctly")
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key)), []).append(row)
    names = sorted(groups, key=lambda n: sum(statistics.fmean(r.get(c) or 0.0 for r in groups[n])
                                             for c in stage_columns))
    plt = style.pyplot()
    fig, ax = plt.subplots(figsize=(6.8, max(2.4, 0.36 * len(names) + 1.5)))
    left = [0.0] * len(names)
    for n, column in enumerate(stage_columns):
        values = [statistics.fmean(r.get(column) or 0.0 for r in groups[name]) * 1000 for name in names]
        ax.barh(names, values, left=left, color=style.CATEGORICAL[n], height=0.62, edgecolor=style.SURFACE,
                linewidth=1.5, label=style.STAGE_LABELS.get(column[8:], column[8:]))
        left = [a + b for a, b in zip(left, values, strict=True)]
    ax.set_xlabel("Mean latency per question (ms)")
    ax.set_title(f"Latency by pipeline stage and {key.replace('_', ' ')}", loc="left")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=min(4, len(stage_columns)))
    return style.save(fig, directory, f"latency_stages_by_{key}")


def tradeoff(rows: list[dict[str, Any]], x: str, y: str, directory: Path, key: str = "technique") -> dict[str, str]:
    xs, ys = dict((n, v) for n, v, _ in _series(rows, key, x)), dict((n, v) for n, v, _ in _series(rows, key, y))
    names = sorted(set(xs) & set(ys))
    if len(names) < 2:
        raise SkipFigure(f"not enough points for {x} vs {y}")
    plt = style.pyplot()
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter([xs[n] for n in names], [ys[n] for n in names], s=52, color=style.PRIMARY,
               edgecolor=style.SURFACE, linewidth=1.5, zorder=3)
    for n in names:
        ax.annotate(n, (xs[n], ys[n]), xytext=(6, 5), textcoords="offset points", fontsize=8, color=style.TEXT)
    ax.set_xlabel(style.label(x))
    ax.set_ylabel(style.label(y))
    ax.set_title(f"{style.label(y)} vs. {style.label(x)}", loc="left")
    ax.margins(0.14)
    return style.save(fig, directory, f"{y}_vs_{x}")


def metric_by_k(rows: list[dict[str, Any]], metric: str, directory: Path) -> dict[str, str]:
    series: dict[str, dict[int, list[float]]] = {}
    for row in rows:
        if row.get(metric) is not None and row.get("k") is not None:
            series.setdefault(str(row["technique"]), {}).setdefault(int(row["k"]), []).append(float(row[metric]))
    ks = sorted({k for values in series.values() for k in values})
    if len(ks) < 2:
        raise SkipFigure("a single k value: nothing to plot over k")
    if len(series) > style.MAX_SERIES:
        raise SkipFigure(f"{len(series)} techniques exceed the {style.MAX_SERIES} distinguishable series; "
                         "export the table instead")
    plt = style.pyplot()
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for n, (name, values) in enumerate(sorted(series.items())):
        points = [(k, statistics.fmean(values[k])) for k in ks if k in values]
        ax.plot([p[0] for p in points], [p[1] for p in points], marker="o", color=style.CATEGORICAL[n], label=name,
                markeredgecolor=style.SURFACE, markeredgewidth=1.5)
    ax.set_xticks(ks)
    if metric in style.BOUNDED:
        ax.set_ylim(0, 1.05)  # coinciding series stay readable through the legend; the table view lists values
    ax.set_xlabel("k (chunks sent to the model)")
    ax.set_ylabel(style.label(metric))
    ax.set_title(f"{style.label(metric)} as k grows", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4)
    return style.save(fig, directory, f"{metric}_by_k")


def metric_vs_feature(rows: list[dict[str, Any]], metric: str, feature: str, directory: Path) -> dict[str, str]:
    """Small multiples (one panel per technique, shared axes) of a metric against a document characteristic."""
    column = f"doc_{feature}"
    techniques = sorted({r["technique"] for r in rows if r.get(column) is not None and r.get(metric) is not None})
    if not techniques or len({r[column] for r in rows if r.get(column) is not None}) < 2:
        raise SkipFigure(f"not enough variation in {feature}")
    plt = style.pyplot()
    cols = min(4, len(techniques))
    lines = (len(techniques) + cols - 1) // cols
    fig, axes = plt.subplots(lines, cols, figsize=(2.6 * cols, 2.3 * lines), sharex=True, sharey=True, squeeze=False)
    for ax in axes.flat[len(techniques):]:
        ax.set_visible(False)
    for ax, technique in zip(axes.flat, techniques, strict=False):
        points = [(r[column], r[metric]) for r in rows if r["technique"] == technique
                  and r.get(column) is not None and r.get(metric) is not None]
        ax.scatter([p[0] for p in points], [p[1] for p in points], s=22, color=style.PRIMARY, alpha=0.75,
                   edgecolor=style.SURFACE, linewidth=0.8)
        ax.set_title(technique, loc="left", fontsize=9)
        if metric in style.BOUNDED:
            ax.set_ylim(-0.08, 1.08)
    fig.supxlabel(f"Document {feature.replace('_', ' ')}", fontsize=9, color=style.TEXT_SECONDARY)
    fig.supylabel(style.label(metric), fontsize=9, color=style.TEXT_SECONDARY)
    fig.suptitle(f"{style.label(metric)} vs. document {feature.replace('_', ' ')}", x=0.02, ha="left",
                 fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return style.save(fig, directory, f"{metric}_vs_doc_{feature}")
