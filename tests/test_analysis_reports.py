import csv
import json

import numpy as np
import pytest

from ragstudio.analysis import characteristics, compare, exports, stats
from ragstudio.config.loader import load
from ragstudio.core.errors import ValidationError
from ragstudio.experiments import runbook
from ragstudio.experiments.runner import Runner
from ragstudio.reports import charts, html_report, style, tables


@pytest.fixture
def finished(populated, runbook_config):
    repo = populated["repo"]
    created = runbook.create(repo, {**runbook_config, "techniques": ["naive", "mmr_rag", "context_compression"],
                                    "k": [2, 4]}, load())
    Runner(repo).execute_runbook(created["id"])
    return repo, created["id"]


def test_paired_test_detects_a_known_effect():
    generator = np.random.default_rng(0)
    a = generator.normal(0.5, 0.1, 40)
    b = a + 0.1 + generator.normal(0, 0.02, 40)
    out = stats.paired_test(a.tolist(), b.tolist())
    assert out["mean_diff"] == pytest.approx(0.1, abs=0.01) and out["ci95"][0] > 0.08 and out["ci95"][1] < 0.12
    assert out["t"]["p_value"] < 1e-6 and out["wilcoxon"]["p_value"] < 1e-6 and out["permutation_p"] < 0.001
    assert out["cohens_dz"] > 3


def test_paired_test_null_and_degenerate_cases():
    generator = np.random.default_rng(1)
    a = generator.normal(0.5, 0.1, 40)
    null = stats.paired_test(a.tolist(), (a + generator.normal(0, 0.05, 40)).tolist())
    assert null["t"]["p_value"] > 0.05 and null["ci95"][0] < 0 < null["ci95"][1]
    same = stats.paired_test([1.0, 0.0, 1.0], [1.0, 0.0, 1.0])
    assert same["mean_diff"] == 0 and same["t"]["p_value"] == 1.0 and same["cohens_dz"] is None
    assert same["wilcoxon"]["n_nonzero"] == 0 and same["permutation_p"] == 1.0
    assert stats.paired_test([1.0], [0.0])["n"] == 1
    with pytest.raises(ValueError):
        stats.paired_test([1.0, 2.0], [1.0])


def test_t_distribution_against_reference_values():
    # two-sided p-values from standard t tables
    assert stats.t_two_sided_p(2.228, 10) == pytest.approx(0.05, abs=5e-4)
    assert stats.t_two_sided_p(2.086, 20) == pytest.approx(0.05, abs=5e-4)
    assert stats.t_two_sided_p(3.169, 10) == pytest.approx(0.01, abs=2e-4)
    assert stats.t_two_sided_p(0.0, 5) == pytest.approx(1.0)


def test_exact_permutation_and_holm_and_spearman():
    assert stats.permutation_p(np.array([1.0, 1.0, 1.0, 1.0])) == pytest.approx(2 / 16)
    assert stats.holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]
    assert stats.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert stats.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert stats.spearman([1, 2, 2, 3], [1, 2, 2, 3]) == 1.0
    assert stats.spearman([1, 1, 1], [1, 2, 3]) is None and stats.spearman([1, 2], [1, 2]) is None


def test_tables_by_run_and_by_question(finished):
    repo, runbook_id = finished
    run_rows = compare.run_table(repo, [runbook_id])
    assert len(run_rows) == 6 and {r["technique"] for r in run_rows} == {"naive", "mmr_rag", "context_compression"}
    assert all(r["chunking"] == "fixed:300/50" and r["latency_generation"] >= 0 for r in run_rows)
    question_rows = compare.question_table(repo, [runbook_id])
    assert len(question_rows) == 36 and {"recall", "f1", "latency_total", "k", "technique"} <= set(question_rows[0])
    by_technique = compare.group_by(run_rows, "technique")
    assert [g["runs"] for g in by_technique] == [2, 2, 2]
    by_k = compare.group_by(run_rows, "k")
    assert [g["k"] for g in by_k] == [2, 4] and by_k[1]["recall"] >= by_k[0]["recall"]
    with pytest.raises(ValidationError):
        compare.group_by(run_rows, "answer")


def test_compare_two_runs(finished):
    repo, runbook_id = finished
    runs = repo.list_runs(runbook_id)
    naive = next(r for r in runs if r["technique"] == "naive" and r["config"]["k"] == 4)
    compression = next(r for r in runs if r["technique"] == "context_compression" and r["config"]["k"] == 4)
    out = compare.compare_runs(repo, naive["id"], compression["id"])
    assert out["config_diff"] == {"technique": {"a": "naive", "b": "context_compression"}}
    assert out["common_questions"] == 6 and out["metrics"]["llm_calls"]["mean_diff"] == 4.0
    assert out["metrics"]["recall"]["n"] == 4 and "permutation_p_holm" in out["metrics"]["f1"]
    same = compare.compare_runs(repo, naive["id"], naive["id"])
    assert same["config_diff"] == {} and same["metrics"]["f1"]["mean_diff"] == 0


def test_characteristics_join(finished):
    repo, runbook_id = finished
    rows = characteristics.joined_rows(repo, [runbook_id])
    assert len(rows) == 36 and {r["target_source"] for r in rows} == {"gold", "top_retrieved"}
    gold = next(r for r in rows if r["question_code"] == "Q1")
    assert gold["target_document"] == "energia-eolica" and gold["doc_chars"] > 1000 and gold["language"] == "pt"
    assert gold["index_chunks"] > 0
    analysis = characteristics.analyze(repo, [runbook_id])
    assert analysis["rows"] == 36 and analysis["documents"] == 3
    assert all(-1 <= c["spearman"] <= 1 and c["n"] >= 3 for c in analysis["correlations"])
    assert {b["bin"] for b in analysis["size_bins"]} <= {"small", "medium", "large"}
    assert {g["language"] for g in analysis["by_language"]} == {"pt"}


def test_exports_register_hash(finished, tmp_path):
    repo, runbook_id = finished
    out = exports.export(repo, "questions", [runbook_id], "csv", str(tmp_path / "q.csv"))
    with open(out["path"], encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 36 and rows[0]["technique"] and out["rows"] == 36
    as_json = exports.export(repo, "runs", [runbook_id], "json", str(tmp_path / "r.json"))
    assert len(json.loads(open(as_json["path"], encoding="utf-8").read())) == 6
    registered = [e for e in repo.list_exports(runbook_id) if e["kind"].startswith("table:")]
    assert {e["sha256"] for e in registered} == {out["sha256"], as_json["sha256"]}
    pytest.importorskip("pyarrow")
    import pandas as pd
    parquet = exports.export(repo, "characteristics", [runbook_id], "parquet", str(tmp_path / "c.parquet"))
    assert len(pd.read_parquet(parquet["path"])) == 36
    with pytest.raises(ValidationError):
        exports.export(repo, "nope", [runbook_id])


def test_tables_formats(finished):
    repo, runbook_id = finished
    rows = compare.group_by(compare.run_table(repo, [runbook_id]), "technique")
    md = tables.markdown(rows)
    assert md.splitlines()[0].startswith("| Technique | Recall@k | MRR") and md.count("\n") == 5
    tex = tables.latex(rows)
    assert r"\toprule" in tex and r"context\_compression" in tex and tex.count(r"\\") == 4
    assert tables.csv_text(rows).splitlines()[0].startswith("technique,recall,mrr")
    assert "judge_accuracy" not in tables.pick(rows, ["technique", "judge_accuracy"])[0], "empty columns are dropped"


def test_figures_and_skip(finished, tmp_path):
    repo, runbook_id = finished
    rows = compare.run_table(repo, [runbook_id])
    files = charts.metric_bars(rows, "recall", tmp_path)
    assert set(files) == {"png", "svg", "pdf"} and all((tmp_path / f"recall_by_technique.{e}").stat().st_size > 500
                                                        for e in files)
    assert charts.latency_stages(rows, tmp_path)["png"].endswith("latency_stages_by_technique.png")
    assert charts.metric_by_k(rows, "recall", tmp_path)["svg"].endswith(".svg")
    assert charts.tradeoff(rows, "latency_mean", "f1", tmp_path)["pdf"].endswith(".pdf")
    with pytest.raises(style.SkipFigure):
        charts.metric_bars(rows, "judge_accuracy", tmp_path)
    with pytest.raises(style.SkipFigure):
        charts.metric_by_k([r for r in rows if r["k"] == 2], "recall", tmp_path)


def test_html_report(finished, tmp_path):
    repo, runbook_id = finished
    out = html_report.generate(repo, [runbook_id], str(tmp_path / "r.html"), "Energy corpus")
    page = open(out["path"], encoding="utf-8").read()
    assert out["figures"] >= 6 and page.count("data:image/png;base64,") == out["figures"]
    for expected in ("<h1>Energy corpus</h1>", "Mock provider", "Experimental setup", "Metric availability",
                     "Contextual Compression", "verified", "judge_accuracy"):
        assert expected in page
    assert "http://" not in page and "https://" not in page, "the report must be self-contained"
    assert [e["kind"] for e in repo.list_exports(runbook_id)][-1] == "report:html"
    with pytest.raises(ValidationError, match="no completed runs"):
        empty = runbook.create(repo, {"name": "e", "corpus": "energia", "question_set": "energia-perguntas"}, load())
        html_report.generate(repo, [empty["id"]])
