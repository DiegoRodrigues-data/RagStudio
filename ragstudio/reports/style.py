"""One visual style for every figure: publication-ready, English labels, PNG 300 dpi + SVG + PDF.

Colors follow a validated categorical order (adjacent-pair colorblind separation checked); a single-series chart
uses slot 1 only. Text always uses ink colors, never a series color.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CATEGORICAL = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
PRIMARY = CATEGORICAL[0]
SURFACE = "#ffffff"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
FORMATS = ("png", "svg", "pdf")
MAX_SERIES = len(CATEGORICAL)

LABELS = {
    "recall": "Recall@k", "precision": "Precision@k", "mrr": "MRR", "ndcg": "nDCG@k", "hit": "Hit@k",
    "context_coverage": "Context coverage", "f1": "Token F1", "accuracy": "Accuracy", "exact_match": "Exact match",
    "faithfulness": "Faithfulness", "groundedness": "Groundedness", "citation_accuracy": "Citation accuracy",
    "hallucination": "Hallucination rate", "refusal": "Refusal rate", "judge_accuracy": "Judge accuracy",
    "judge_faithfulness": "Judge faithfulness", "latency_mean": "Mean latency (s)",
    "llm_calls_per_question": "LLM calls per question", "cost_usd": "Cost (USD)",
    "context_chars_mean": "Context size (chars)", "latency_total": "Latency (s)",
}
BOUNDED = frozenset({"recall", "precision", "mrr", "ndcg", "hit", "context_coverage", "f1", "accuracy", "exact_match",
                     "faithfulness", "groundedness", "citation_accuracy", "hallucination", "refusal",
                     "judge_accuracy", "judge_faithfulness"})
STAGE_LABELS = {"query_transform": "Query transform", "retrieval": "Retrieval", "rerank": "Rerank",
                "compression": "Compression", "context": "Context assembly", "generation": "Generation",
                "control": "Control", "index_build": "Index build"}


class SkipFigure(Exception):
    """Raised when a figure has no data: the report skips it instead of failing."""


def label(metric: str) -> str:
    return LABELS.get(metric, metric.replace("_", " ").capitalize())


def pyplot() -> Any:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold",
        "axes.labelsize": 9, "axes.labelcolor": TEXT_SECONDARY, "axes.edgecolor": GRID, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "xtick.color": TEXT_SECONDARY, "ytick.color": TEXT_SECONDARY,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "text.color": TEXT, "legend.frameon": False,
        "legend.fontsize": 8, "lines.linewidth": 2.0, "lines.markersize": 6, "svg.fonttype": "none",
        "pdf.fonttype": 42,
    })
    return plt


def save(fig: Any, directory: Path, name: str) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    out = {}
    for fmt in FORMATS:
        path = directory / f"{name}.{fmt}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        out[fmt] = str(path)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return out
