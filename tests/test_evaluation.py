import pytest

from ragstudio.evaluation import evaluate_result, generation_metrics, retrieval_metrics
from ragstudio.evaluation.aggregate import aggregate, quadrant
from ragstudio.evaluation.availability import availability
from ragstudio.evaluation.judge import Judge, parse_score
from ragstudio.providers.routing import resolve_endpoint


def chunk(doc, start, end, text="irrelevante"):
    return {"document_id": doc, "char_start": start, "char_end": end, "text": text}


GOLD = [{"document_id": "a", "text": "o limite é 59,3%", "char_start": 100, "char_end": 116},
        {"document_id": "b", "text": "Resolução 482", "char_start": None, "char_end": None}]


def test_retrieval_metrics_hand_computed():
    chunks = [chunk("a", 0, 50), chunk("a", 90, 200), chunk("b", 0, 40, "A Resolução  482 da ANEEL"), chunk("c", 0, 9)]
    m = retrieval_metrics.evaluate(chunks, GOLD, "limite 59,3% resolução 482")
    assert (m["k"], m["gold_count"], m["hit"], m["recall"], m["precision"], m["mrr"]) == (4, 2, 1.0, 1.0, 0.5, 0.5)
    dcg = 1 / 1.5849625007211562 + 1 / 2.0   # relevant at ranks 2 and 3
    idcg = 1 / 1.0 + 1 / 1.5849625007211562
    assert m["ndcg"] == pytest.approx(dcg / idcg, abs=1e-4) and m["context_coverage"] == 1.0


def test_retrieval_metrics_misses_and_partial():
    m = retrieval_metrics.evaluate([chunk("a", 0, 50), chunk("c", 0, 9)], GOLD, "nada")
    assert (m["hit"], m["recall"], m["precision"], m["mrr"], m["ndcg"], m["context_coverage"]) == (0, 0, 0, 0, 0, 0)
    half = retrieval_metrics.evaluate([chunk("a", 104, 300)], GOLD)
    assert half["recall"] == 0.5 and half["mrr"] == 1.0
    assert retrieval_metrics.evaluate([chunk("a", 110, 300)], GOLD)["hit"] == 0.0     # covers < 50% of the gold span
    assert retrieval_metrics.evaluate([chunk("x", 100, 116)], GOLD)["hit"] == 0.0     # right offsets, wrong document
    assert retrieval_metrics.evaluate([], GOLD)["precision"] == 0.0


def test_no_gold_means_no_retrieval_metrics():
    assert retrieval_metrics.evaluate([chunk("a", 0, 5)], []) is None


CONTEXT = ("[1] (a · chunk 0)\nO limite de Betz estabelece que o aproveitamento máximo teórico é de 59,3%.\n\n"
           "[2] (b · chunk 1)\nA usina de Itaipu possui 20 unidades geradoras.")


def test_generation_metrics_grounded_answer():
    answer = "O limite de Betz estabelece que o aproveitamento máximo teórico é de 59,3%. [1]"
    m = generation_metrics.evaluate(answer, CONTEXT, "O aproveitamento máximo teórico é de 59,3%.", "extraction")
    assert m["faithfulness"] == 1.0 and m["groundedness"] == 1.0 and m["citation_accuracy"] == 1.0
    assert m["hallucination"] == 0.0 and m["refusal"] == 0.0 and m["exact_match"] == 1.0
    assert 0.6 < m["f1"] < 1.0 and m["accuracy"] == m["f1"]


def test_generation_metrics_bad_answers():
    wrong_cite = generation_metrics.evaluate("O limite de Betz é de 59,3%. [2]", CONTEXT, None)
    assert wrong_cite["citation_accuracy"] == 0.0 and wrong_cite["f1"] is None and wrong_cite["exact_match"] is None
    invented = generation_metrics.evaluate("Geralmente o limite fica em torno de 72% segundo estudos recentes.", CONTEXT, None)
    assert invented["hallucination"] == 1.0 and invented["faithfulness"] == 0.0
    assert generation_metrics.evaluate("O valor é 72%.", CONTEXT, None)["hallucination"] == 1.0
    refusal = generation_metrics.evaluate("Não encontrei essa informação no contexto.", CONTEXT, "x")
    assert refusal["refusal"] == 1.0 and refusal["citation_accuracy"] is None
    assert generation_metrics.evaluate("", CONTEXT, None)["faithfulness"] is None


def test_boolean_and_classification_accuracy():
    assert generation_metrics.accuracy("Sim, há previsão.", "sim", "boolean") == 1.0
    assert generation_metrics.accuracy("Não.", "sim", "boolean") == 0.0
    assert generation_metrics.exact_match("Não há.", "não", "boolean") == 1.0
    assert generation_metrics.accuracy("A turbina é do tipo Pelton.", "pelton", "classification") == 1.0


def test_availability_never_invents():
    none = availability([{"text": "q"}])
    assert "recall" in none["requires_annotation"] and "f1" in none["requires_annotation"]
    assert "recall" not in none["available"] and "faithfulness" in none["available"]
    mixed = availability([{"gold_passages": [{}], "expected_answer": "x"}, {"text": "q"}], judge=True)
    assert "recall" in mixed["available"] and "computed on 1 of 2" in mixed["partial"]["recall"]
    assert "judge_accuracy" in mixed["available"] and "judge_accuracy" not in mixed["requires_annotation"]


def test_evaluate_result_without_annotations_returns_none_metrics():
    retrieval, generation = evaluate_result({"text": "q"}, "resposta", CONTEXT, [chunk("a", 0, 5)])
    assert retrieval is None and generation["f1"] is None and generation["accuracy"] is None


def test_aggregate_keeps_none_for_unmeasured():
    rows = [{"recall": 1.0, "f1": None, "faithfulness": 0.9, "accuracy": None, "latency_total": 0.2, "llm_calls": 2,
             "prompt_tokens": 10, "completion_tokens": 5, "embedding_tokens": 1, "cost_usd": 0.01, "context_chars": 100,
             "timings": [{"stage": "retrieval", "seconds": 0.1}, {"stage": "generation", "seconds": 0.1}]},
            {"recall": 0.0, "f1": None, "faithfulness": 0.7, "accuracy": None, "latency_total": 0.4, "llm_calls": 4,
             "prompt_tokens": 10, "completion_tokens": 5, "embedding_tokens": 1, "cost_usd": 0.03, "context_chars": 300,
             "timings": [{"stage": "retrieval", "seconds": 0.3}]},
            {"error": "boom", "recall": None, "timings": []}]
    agg = aggregate(rows)
    assert agg["n_questions"] == 3 and agg["n_failed"] == 1
    assert agg["recall"] == 0.5 and agg["recall_n"] == 2 and agg["f1"] is None and agg["f1_n"] == 0
    assert agg["latency_mean"] == pytest.approx(0.3) and agg["llm_calls_per_question"] == 3.0
    assert agg["latency_by_stage"] == {"retrieval": 0.2, "generation": 0.05}
    assert agg["cost_usd"] == pytest.approx(0.04) and agg["quadrant"] is None
    assert aggregate([{**rows[0], "cost_usd": None}])["cost_usd"] is None
    assert aggregate([]) == {"n_questions": 0, "n_failed": 0}
    assert quadrant(0.8, 0.8) == "Correct and grounded" and quadrant(0.8, 0.1) == "Correct but ungrounded"


def test_judge_with_mock_and_score_parsing():
    assert [parse_score(s) for s in ("0.8", "Nota: 7", "85", "sem nota", "0,25")] == [0.8, 0.7, 0.85, None, 0.25]
    judge = Judge(resolve_endpoint("llm"))
    out = judge.evaluate("q", "o limite de Betz é 59,3%", CONTEXT, "limite de Betz 59,3%")
    assert out["judge_model"] == "mock-llm" and 0 < out["judge_accuracy"] <= 1 and out["judge_faithfulness"] == 1.0
    assert judge.evaluate("q", "resposta", CONTEXT, None)["judge_accuracy"] is None
    assert judge.usage["llm_calls"] == 3
