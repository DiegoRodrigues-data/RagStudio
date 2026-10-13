"""Self-contained HTML report (figures embedded as base64) for one or more runbooks."""
from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import __version__
from ..analysis import characteristics, compare
from ..core import paths, registry
from ..core.errors import ValidationError
from ..core.hashing import sha256_file
from ..db.repository import Repo
from . import charts, style, tables

TEMPLATE = Path(__file__).with_name("template.html")
RUN_COLUMNS = ("seq", "technique", "retrieval_mode", "reranker", "k", "seed", "chunking", "llm", "embedding_model",
               "recall", "mrr", "f1", "faithfulness", "latency_mean", "llm_calls_per_question", "cost_usd",
               "n_questions", "n_failed")


def html_table(rows: list[dict[str, Any]], columns: tuple[str, ...] | list[str]) -> str:
    header, body = tables.pick(rows, columns)
    if not header:
        return "<p class='muted'>No data.</p>"
    head = "".join(f"<th>{html.escape(style.label(c) if c in style.LABELS else c.replace('_', ' '))}</th>"
                   for c in header)
    lines = "".join("<tr>" + "".join(f"<td>{html.escape(tables._fmt(v))}</td>" for v in row) + "</tr>"
                    for row in body)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{lines}</tbody></table>"


def build_figures(run_rows: list[dict[str, Any]], char_rows: list[dict[str, Any]],
                  directory: Path) -> tuple[list[dict[str, Any]], list[str]]:
    plan = [
        ("Recall@k of the final context, by technique.", lambda: charts.metric_bars(run_rows, "recall", directory)),
        ("Mean reciprocal rank of the first relevant chunk, by technique.",
         lambda: charts.metric_bars(run_rows, "mrr", directory)),
        ("Token F1 against the expected answer, by technique.", lambda: charts.metric_bars(run_rows, "f1", directory)),
        ("Lexical faithfulness of the answer to its context, by technique.",
         lambda: charts.metric_bars(run_rows, "faithfulness", directory)),
        ("LLM calls needed per question, by technique.",
         lambda: charts.metric_bars(run_rows, "llm_calls_per_question", directory)),
        ("Mean latency per question split by pipeline stage.", lambda: charts.latency_stages(run_rows, directory)),
        ("Answer quality against latency: up and to the left is better.",
         lambda: charts.tradeoff(run_rows, "latency_mean", "f1", directory)),
        ("Recall as more chunks are sent to the model.", lambda: charts.metric_by_k(run_rows, "recall", directory)),
        ("Recall against the size of the target document, one panel per technique.",
         lambda: charts.metric_vs_feature(char_rows, "recall", "chars", directory)),
    ]
    figures, skipped = [], []
    for caption, build in plan:
        try:
            files = build()
        except style.SkipFigure as exc:
            skipped.append(str(exc))
            continue
        figures.append({"caption": caption, "files": files})
    return figures, skipped


def generate(repo: Repo, runbook_refs: list[str], output: str | None = None,
             title: str | None = None) -> dict[str, Any]:
    try:
        from jinja2 import Template
    except ImportError as exc:
        raise ValidationError("HTML reports need jinja2 (pip install jinja2)") from exc
    runbooks = [repo.get_runbook(ref) for ref in runbook_refs]
    run_rows = registry.with_titles(compare.run_table(repo, [rb["id"] for rb in runbooks]))
    if not run_rows:
        raise ValidationError("no completed runs in the given runbooks")
    char = characteristics.analyze(repo, [rb["id"] for rb in runbooks])
    char["correlations"] = registry.with_titles(char.get("correlations", []))
    char_rows = registry.with_titles(characteristics.joined_rows(repo, [rb["id"] for rb in runbooks]))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    figure_dir = paths.figures_dir() / f"report_{stamp}"
    figures, skipped = build_figures(run_rows, char_rows, figure_dir)
    for figure in figures:
        figure["data"] = base64.b64encode(Path(figure["files"]["png"]).read_bytes()).decode("ascii")

    first_run = repo.get_run(run_rows[0]["run_id"])
    snapshot = repo.get_snapshot(first_run["id"]) or {}
    record = repo.run_metrics(first_run["id"]) or {}
    corpus = repo.get_corpus(first_run["config"]["corpus"])
    profile = corpus["profile"]
    providers = sorted({(repo.get_snapshot(r["run_id"]) or {}).get("llm", {}).get("provider", "?") for r in run_rows})
    setup = {
        "Runbooks": ", ".join(f"{rb['name']} ({rb['id']})" for rb in runbooks),
        "Completed runs": len(run_rows), "Techniques": ", ".join(sorted({r["technique"] for r in run_rows})),
        "LLM": ", ".join(sorted({str(r["llm"] or snapshot.get("llm", {}).get("model")) for r in run_rows})),
        "Embedding model": ", ".join(sorted({str(r["embedding_model"] or snapshot.get("embedder", {}).get("model"))
                                             for r in run_rows})),
        "Provider": ", ".join(providers), "Chunking": ", ".join(sorted({r["chunking"] for r in run_rows})),
        "Retrieval modes": ", ".join(sorted({str(r["retrieval_mode"]) for r in run_rows})),
        "k": ", ".join(str(k) for k in sorted({r["k"] for r in run_rows})),
        "Seeds": ", ".join(str(s) for s in sorted({r["seed"] for r in run_rows})),
        "Python": snapshot.get("python_version"), "Platform": snapshot.get("platform"),
        "Packages": ", ".join(f"{k} {v}" for k, v in (snapshot.get("packages") or {}).items()),
        "Git commit": snapshot.get("git_commit") or "not a git checkout",
    }
    corpus_info = {"Name": corpus["name"], "Documents": profile.get("documents"),
                   "Total characters": profile.get("total_chars"), "Languages": profile.get("languages"),
                   "Formats": profile.get("formats"),
                   "Document size (chars)": profile.get("chars"), "Content hash": corpus["content_hash"]}
    evidence = [{"run": r["run_id"], "technique": r["technique"], "config_hash": r["config_hash"][:16],
                 "events": (chain := repo.verify_chain(r["run_id"]))["events"],
                 "chain": "verified" if chain["ok"] else f"BROKEN at {chain.get('broken_at_seq')}",
                 "head": chain.get("head", "")[:16]} for r in run_rows]
    page = Template(TEMPLATE.read_text(encoding="utf-8")).render(
        title=title or f"RagStudio report: {', '.join(rb['name'] for rb in runbooks)}",
        subtitle=f"{len(run_rows)} runs over corpus “{corpus['name']}”, {record.get('metrics', {}).get('n_questions', '?')} "
                 f"questions per run.",
        mock="mock" in providers, results_table=html_table(compare.group_by(run_rows, "technique"),
                                                           ("technique", "runs", *tables.DEFAULT_COLUMNS[1:])),
        runs_table=html_table(run_rows, RUN_COLUMNS), figures=figures, skipped=skipped,
        availability=record.get("availability") or {"questions": 0, "available": []}, characteristics=char,
        correlations_table=html_table(char["correlations"][:20],
                                      ("technique", "metric", "feature", "spearman", "n", "documents")),
        setup=setup, corpus=corpus_info,
        evidence_table=html_table(evidence, ("run", "technique", "config_hash", "events", "chain", "head")),
        version=__version__, generated=datetime.now().strftime("%Y-%m-%d %H:%M"))
    path = Path(output).expanduser() if output else paths.exports_dir() / f"report_{stamp}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    digest = sha256_file(path)
    repo.add_export("report:html", ",".join(rb["id"] for rb in runbooks), "html", str(path), digest)
    return {"path": str(path), "sha256": digest, "runs": len(run_rows), "figures": len(figures),
            "figures_dir": str(figure_dir), "skipped_figures": skipped}
