"""`ragstudio reports ...`: HTML report, figures, tables and analytical exports."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from ..analysis import characteristics, compare, exports
from ..core import paths, registry
from ..core.errors import ValidationError
from ..db.repository import Repo
from ..reports import html_report, tables
from .common import command, csv_list


def _html(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return html_report.generate(repo, csv_list(args.runbook_ids), args.output, args.title)


def _figures(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        refs = csv_list(args.runbook_ids)
        run_rows = registry.with_titles(compare.run_table(repo, refs))
        if not run_rows:
            raise ValidationError("no completed runs in the given runbooks")
        directory = Path(args.output).expanduser() if args.output else \
            paths.figures_dir() / f"figures_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        figures, skipped = html_report.build_figures(
            run_rows, registry.with_titles(characteristics.joined_rows(repo, refs)), directory)
    return {"directory": str(directory), "figures": [{"caption": f["caption"], **f["files"]} for f in figures],
            "skipped": skipped}


def _tables(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        rows = compare.group_by(compare.run_table(repo, csv_list(args.runbook_ids)), args.by)
    if not rows:
        raise ValidationError("no completed runs in the given runbooks")
    if args.format != "csv":  # CSV is data: it keeps the identifier
        rows = registry.with_titles(rows)
    columns = [args.by, *tables.DEFAULT_COLUMNS[1:]]
    render = {"markdown": tables.markdown, "latex": tables.latex, "csv": tables.csv_text}[args.format]
    text = render(rows, columns)
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
    return {"format": args.format, "rows": len(rows), "path": args.output, "text": text}


def _export(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return exports.export(repo, args.table, csv_list(args.runbook_ids), args.format, args.output)


def _schema(args: argparse.Namespace) -> Any:
    return exports.SCHEMA


def _list(args: argparse.Namespace) -> Any:
    with Repo() as repo:
        return repo.list_exports()


def register(groups: Any) -> None:
    sub = groups.add_parser("reports", help="reports, figures, tables, exports").add_subparsers(dest="command",
                                                                                                required=True)
    p = command(sub, "html", _html, "self-contained HTML report")
    p.add_argument("--runbook-ids", required=True)
    p.add_argument("--output")
    p.add_argument("--title")
    p = command(sub, "figures", _figures, "figures as PNG (300 dpi), SVG and PDF")
    p.add_argument("--runbook-ids", required=True)
    p.add_argument("--output", help="directory")
    p = command(sub, "tables", _tables, "result table as Markdown, LaTeX or CSV")
    p.add_argument("--runbook-ids", required=True)
    p.add_argument("--by", default="technique", choices=compare.GROUP_KEYS)
    p.add_argument("--format", default="markdown", choices=("markdown", "latex", "csv"))
    p.add_argument("--output")
    p = command(sub, "export", _export, "analytical table as CSV, JSON or Parquet")
    p.add_argument("--runbook-ids", required=True)
    p.add_argument("--table", default="questions", choices=exports.TABLES)
    p.add_argument("--format", default="csv", choices=exports.FORMATS)
    p.add_argument("--output")
    command(sub, "schema", _schema, "columns of each exported table")
    command(sub, "list", _list, "exports registered in the database (path + SHA-256)")
