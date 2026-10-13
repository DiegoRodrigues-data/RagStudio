import json

import pytest

from ragstudio.core.errors import LeakageError, ValidationError
from ragstudio.ingest import questions as qf
from ragstudio.ingest.cleaner import clean
from ragstudio.ingest.loaders import load_path
from ragstudio.ingest.profile import corpus_profile, detect_language, document_profile
from ragstudio.ingest.splits import assert_disjoint, make_splits, select_questions, splits_hash
from ragstudio.processing.normalize import prepare


def test_load_directory(documents):
    assert [d.id for d in documents] == ["energia-eolica", "energia-solar", "hidreletricas"]
    assert all(d.format == "markdown" and d.chars == len(d.text) and len(d.sha256) == 64 for d in documents)


def test_loaders_txt_json_and_errors(tmp_path):
    (tmp_path / "a.txt").write_text("linha um\r\nlinha dois  \n", encoding="utf-8")
    (tmp_path / "c.jsonl").write_text(json.dumps({"id": "X 1", "text": "conteúdo", "court": "TJ"}) + "\n", "utf-8")
    (tmp_path / "skip.bin").write_bytes(b"\x00")
    (tmp_path / "empty.md").write_text("   \n", encoding="utf-8")
    docs, warnings = load_path(tmp_path)
    assert {d.id: d.format for d in docs} == {"a": "text", "x-1": "json"}
    assert docs[0].text == "linha um\nlinha dois\n" and docs[1].metadata == {"court": "TJ"}
    assert len(warnings) == 2 and any("skip.bin: unsupported format" in w for w in warnings)
    with pytest.raises(ValidationError, match="no files found"):
        (tmp_path / "void").mkdir()
        load_path(tmp_path / "void")
    with pytest.raises(ValidationError, match="path not found"):
        load_path(tmp_path / "nope")
    with pytest.raises(ValidationError, match="is empty"):
        load_path(tmp_path / "empty.md")
    with pytest.raises(ValidationError, match="unsupported format"):
        load_path(tmp_path / "skip.bin")


def test_pdf_loader_reports_missing_docling(tmp_path, monkeypatch):
    import sys

    from ragstudio.ingest.loaders import pdf_docling
    monkeypatch.setattr(pdf_docling, "_converter", None)
    monkeypatch.setitem(sys.modules, "docling.datamodel.pipeline_options", None)  # import raises ImportError
    (tmp_path / "x.pdf").write_bytes(b"%PDF-1.4")
    with pytest.raises(ValidationError, match="needs Docling"):
        load_path(tmp_path / "x.pdf")
    (tmp_path / "y.pdf").write_bytes(b"%PDF-1.4")
    events = []
    with pytest.raises(ValidationError) as info:      # a folder of PDFs must say WHY nothing was loaded
        load_path(tmp_path, progress=events.append)
    assert "none of the 2 file(s)" in str(info.value) and "2 file(s): PDF loading needs Docling" in str(info.value)
    assert [e["event"] for e in events] == ["file_started", "file", "file_started", "file"]
    assert events[-1] == {"event": "file", "done": 2, "total": 2, "name": "y.pdf", "ok": False}


def test_cleaner_flags():
    text = "Tribunal X\n\n![img](a.png)\nTexto.\n\n\n\nPágina 3 de 10\nTribunal X\nTribunal X\nTribunal X\nFim.\n"
    out = clean(text)
    assert "![img]" not in out and "Página 3" not in out and "\n\n\n" not in out and out.count("Tribunal X") == 1
    assert clean(text, ["collapse_blank_lines"]).count("Tribunal X") == 4
    with pytest.raises(ValueError):
        clean(text, ["nope"])


def test_profile(documents):
    profile = document_profile(documents[0])
    assert profile["language"] == "pt" and profile["headings"] == 5 and profile["words"] > 100
    assert detect_language("The quick brown fox is on the table and it was there for the day") == "en"
    assert detect_language("abc") == "und"
    corpus = corpus_profile([document_profile(d) for d in documents])
    assert corpus["documents"] == 3 and corpus["languages"] == {"pt": 3} and corpus["formats"] == {"markdown": 3}
    cleaned, p = prepare(documents[0], ["collapse_blank_lines"])
    assert cleaned.language == "pt" and p["chars"] == cleaned.chars


def test_splits_are_deterministic_disjoint_and_stratified():
    ids = [f"d{i}" for i in range(20)]
    a = make_splits(ids, {"train": 0.6, "validation": 0.2, "test": 0.2}, seed=7)
    assert a == make_splits(ids, {"train": 0.6, "validation": 0.2, "test": 0.2}, seed=7)
    assert a != make_splits(ids, {"train": 0.6, "validation": 0.2, "test": 0.2}, seed=8)
    assert [len(a[s]) for s in ("train", "validation", "test")] == [12, 4, 4]
    assert sorted(sum(a.values(), [])) == sorted(ids)
    assert_disjoint(a)
    assert splits_hash(a) == splits_hash({k: list(reversed(v)) for k, v in a.items()})
    strata = {d: ("x" if i < 10 else "y") for i, d in enumerate(ids)}
    s = make_splits(ids, {"train": 0.5, "test": 0.5}, seed=1, strata=strata)
    assert sum(1 for d in s["test"] if strata[d] == "x") == 5
    with pytest.raises(LeakageError):
        assert_disjoint({"train": ["a"], "test": ["a"]})
    with pytest.raises(ValidationError):
        make_splits(ids, {"holdout": 1.0})


def test_select_questions_detects_leak():
    q = lambda code, split, doc: {"code": code, "split": split,  # noqa: E731
                                  "gold_passages": [{"document_id": doc}] if doc else []}
    questions = [q("A", "test", "d1"), q("B", "train", "d2"), q("C", None, "d1"), q("D", None, "d9"), q("E", None, None)]
    assert [x["code"] for x in select_questions(questions, "test", ["d1"])] == ["A", "C", "E"]
    with pytest.raises(LeakageError, match="outside it"):
        select_questions([q("L", "test", "d2")], "test", ["d1"])


def test_question_file_parsing_and_anchoring(question_file, documents):
    parsed = qf.parse_file(question_file)
    assert parsed["name"] == "energia-perguntas" and len(parsed["questions"]) == 6
    assert qf.anchor_gold(parsed["questions"], documents) == []
    by_id = {d.id: d for d in documents}
    for question in parsed["questions"]:
        for gold in question["gold_passages"]:
            assert by_id[gold["document_id"]].text[gold["char_start"]:gold["char_end"]] == gold["text"]


def test_anchor_tolerates_whitespace_and_rejects_missing(documents):
    ok = [qf.parse_question({"text": "?", "gold_passages": [
        {"document_id": "energia-eolica", "text": "o   aproveitamento MAXIMO teorico e de 59,3%"}]})]
    qf.anchor_gold(ok, documents)
    assert ok[0]["gold_passages"][0]["text"] == "o aproveitamento máximo teórico é de 59,3%"
    bad = [qf.parse_question({"text": "?", "gold_passages": [{"document_id": "energia-eolica", "text": "inexistente"}]})]
    with pytest.raises(ValidationError, match="not found literally"):
        qf.anchor_gold(bad, documents)
    with pytest.raises(ValidationError, match="unknown document"):
        qf.anchor_gold([qf.parse_question({"text": "?", "gold_passages": [{"document_id": "z", "text": "x"}]})],
                       documents)


def test_legacy_question_keys():
    q = qf.parse_question({"id": "L1", "text": "t", "resposta_esperada": "sim", "tipo_resposta": "boolean",
                           "task_type": "x"})
    assert (q["code"], q["expected_answer"], q["answer_type"], q["metadata"]) == ("L1", "sim", "boolean",
                                                                                 {"task_type": "x"})
    with pytest.raises(ValidationError):
        qf.parse_question({"text": "t", "answer_type": "essay"})
