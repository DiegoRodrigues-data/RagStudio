"""Tables in Markdown, LaTeX (booktabs) and CSV built from the comparison rows."""
from __future__ import annotations

import csv
import io
from typing import Any

from . import style

DEFAULT_COLUMNS = ("technique", "recall", "mrr", "ndcg", "f1", "accuracy", "faithfulness", "latency_mean",
                   "llm_calls_per_question", "cost_usd")


def _fmt(value: Any) -> str:
    if value is None:
        return "–"
    if isinstance(value, float):
        if value != 0 and abs(value) < 0.01:
            return f"{value:.2g}"
        return f"{value:.3f}" if abs(value) < 100 else f"{value:.1f}"
    return str(value)


def pick(rows: list[dict[str, Any]], columns: tuple[str, ...] | list[str] | None = None) -> tuple[list[str], list[list[Any]]]:
    """Columns that exist and have at least one value, in the requested order."""
    wanted = list(columns or DEFAULT_COLUMNS)
    kept = [c for c in wanted if any(row.get(c) is not None for row in rows)]
    return kept, [[row.get(c) for c in kept] for row in rows]


def markdown(rows: list[dict[str, Any]], columns: tuple[str, ...] | list[str] | None = None) -> str:
    header, body = pick(rows, columns)
    lines = ["| " + " | ".join(style.label(c) if c != "technique" else "Technique" for c in header) + " |",
             "|" + "|".join("---" if i == 0 else "---:" for i in range(len(header))) + "|"]
    lines += ["| " + " | ".join(_fmt(v) for v in row) + " |" for row in body]
    return "\n".join(lines) + "\n"


def latex(rows: list[dict[str, Any]], columns: tuple[str, ...] | list[str] | None = None,
          caption: str = "Results by technique.", label: str = "tab:results") -> str:
    header, body = pick(rows, columns)
    escape = lambda s: str(s).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&").replace("@", "@")  # noqa: E731
    out = [r"\begin{table}[t]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
           r"\begin{tabular}{l" + "r" * (len(header) - 1) + "}", r"\toprule",
           " & ".join(escape(style.label(c) if c != "technique" else "Technique") for c in header) + r" \\",
           r"\midrule"]
    out += [" & ".join(escape(_fmt(v)).replace("–", "--") for v in row) + r" \\" for row in body]
    out += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(out) + "\n"


def csv_text(rows: list[dict[str, Any]], columns: tuple[str, ...] | list[str] | None = None) -> str:
    header, body = pick(rows, columns)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(body)
    return buffer.getvalue()
