from typing import Any, Dict, List
from .types import RAGInput, RAGOutput, Doc
from .prompts import (

    format_context,
    prompt_answer_only_from_context,
    prompt_make_multi_queries,
    prompt_make_hypo_doc,
    prompt_decompose,
    prompt_extract_essential,
    prompt_gap_query,
)

from .evo_utils import heuristic_confidence, llm_confidence, log_rag_evo
from .evo_heuristics import confidence_score

def _get(inp: RAGInput, key: str, default: Any):
    return inp[key] if key in inp else default


def rag_naive(inp: RAGInput) -> RAGOutput:
    q = inp["query"]
    k = _get(inp, "k", 8)
    filters = _get(inp, "filters", None)
    maxc = _get(inp, "max_context_chars", 12000)

    docs = inp["retriever"](q, k, filters)
    if inp.get("reranker"):
        docs = inp["reranker"](q, docs, k)

    ctx = format_context(docs, maxc)
    ans = inp["llm"](prompt_answer_only_from_context(q, ctx))

    return {
        "answer": ans,
        "contexts": docs,
        "citations": [{"doc_id": d.get("doc_id"), "chunk_id": d.get("chunk_id"), "source_path": d.get("source_path")} for d in docs],
        "diagnostics": {"algo": "naive", "k": k},
    }


def rag_hyde(inp: RAGInput) -> RAGOutput:
    q = inp["query"]
    k = _get(inp, "k", 8)
    filters = _get(inp, "filters", None)
    maxc = _get(inp, "max_context_chars", 12000)

    hypo = inp["llm"](prompt_make_hypo_doc(q))
    docs = inp["retriever"](hypo, k, filters)
    if inp.get("reranker"):
        docs = inp["reranker"](q, docs, k)

    ctx = format_context(docs, maxc)
    ans = inp["llm"](prompt_answer_only_from_context(q, ctx))

    return {
        "answer": ans,
        "contexts": docs,
        "citations": [{"doc_id": d.get("doc_id"), "chunk_id": d.get("chunk_id"), "source_path": d.get("source_path")} for d in docs],
        "diagnostics": {"algo": "hyde", "hypo_len": len(hypo)},
    }


def rag_multi_query(inp: RAGInput) -> RAGOutput:
    q = inp["query"]
    k = _get(inp, "k", 8)
    filters = _get(inp, "filters", None)
    maxc = _get(inp, "max_context_chars", 12000)
    n = inp.get("extra", {}).get("n_queries", 4)

    raw = inp["llm"](prompt_make_multi_queries(q, n))
    queries = [line.strip() for line in raw.splitlines() if line.strip()]
    queries = ([q] + queries)[:n]

    pool: Dict[str, Doc] = {}
    for qq in queries:
        for d in inp["retriever"](qq, k, filters):
            pool[str(d.get("id"))] = d

    docs = list(pool.values())
    if inp.get("reranker"):
        docs = inp["reranker"](q, docs, k)
    else:
        docs = docs[:k]

    ctx = format_context(docs, maxc)
    ans = inp["llm"](prompt_answer_only_from_context(q, ctx))

    return {
        "answer": ans,
        "contexts": docs,
        "citations": [{"doc_id": d.get("doc_id"), "chunk_id": d.get("chunk_id"), "source_path": d.get("source_path")} for d in docs],
        "diagnostics": {"algo": "multi_query", "queries": queries},
    }


def rag_decomposition(inp: RAGInput) -> RAGOutput:
    q = inp["query"]
    k = _get(inp, "k", 8)
    filters = _get(inp, "filters", None)
    maxc = _get(inp, "max_context_chars", 12000)
    m = inp.get("extra", {}).get("n_subquestions", 4)

    raw = inp["llm"](prompt_decompose(q, m))
    subqs = [line.strip() for line in raw.splitlines() if line.strip()]
    subqs = subqs[:m]

    pool: Dict[str, Doc] = {}
    for sq in subqs:
        for d in inp["retriever"](sq, max(2, k // 2), filters):
            pool[str(d.get("id"))] = d

    docs = list(pool.values())
    if inp.get("reranker"):
        docs = inp["reranker"](q, docs, k)

    ctx = format_context(docs, maxc)
    ans = inp["llm"](prompt_answer_only_from_context(q, ctx))

    return {
        "answer": ans,
        "contexts": docs,
        "citations": [{"doc_id": d.get("doc_id"), "chunk_id": d.get("chunk_id"), "source_path": d.get("source_path")} for d in docs],
        "diagnostics": {"algo": "decomposition", "subqs": subqs},
    }


def rag_iterative(inp: RAGInput) -> RAGOutput:
    q = inp["query"]
    k = _get(inp, "k", 8)
    filters = _get(inp, "filters", None)
    maxc = _get(inp, "max_context_chars", 12000)
    rounds = inp.get("extra", {}).get("rounds", 2)

    pool: Dict[str, Doc] = {}
    cur_query = q
    last = ""

    for _ in range(rounds):
        for d in inp["retriever"](cur_query, k, filters):
            pool[str(d.get("id"))] = d

        docs = list(pool.values())
        if inp.get("reranker"):
            docs = inp["reranker"](q, docs, k)
        else:
            docs.sort(key=lambda x: x.get("score", 0), reverse=True)
            docs = docs[:k]

        ctx = format_context(docs, maxc)
        last = inp["llm"](prompt_answer_only_from_context(q, ctx))
        cur_query = (inp["llm"](prompt_gap_query(q, last)).strip() or q)

    final_docs = list(pool.values())
    if inp.get("reranker"):
        final_docs = inp["reranker"](q, final_docs, k)
    else:
        final_docs.sort(key=lambda x: x.get("score", 0), reverse=True)
        final_docs = final_docs[:k]

    return {
        "answer": last,
        "contexts": final_docs,
        "citations": [{"doc_id": d.get("doc_id"), "chunk_id": d.get("chunk_id"), "source_path": d.get("source_path")} for d in final_docs],
        "diagnostics": {"algo": "iterative", "rounds": rounds},
    }


def rag_context_compression(inp: RAGInput) -> RAGOutput:
    q = inp["query"]
    k = _get(inp, "k", 8)
    filters = _get(inp, "filters", None)
    maxc = _get(inp, "max_context_chars", 12000)

    docs = inp["retriever"](q, k * 3, filters)
    if inp.get("reranker"):
        docs = inp["reranker"](q, docs, k * 2)

    compressed: List[Doc] = []
    for d in docs[:k]:
        text = d.get("text", "")
        snippet = inp["llm"](prompt_extract_essential(q, text[:5000]))
        compressed.append({**d, "text": snippet})

    ctx = format_context(compressed, maxc)
    ans = inp["llm"](prompt_answer_only_from_context(q, ctx))

    return {
        "answer": ans,
        "contexts": compressed,
        "citations": [{"doc_id": d.get("doc_id"), "chunk_id": d.get("chunk_id"), "source_path": d.get("source_path")} for d in compressed],
        "diagnostics": {"algo": "context_compression"},
    }


def rag_evo(inp: RAGInput) -> RAGOutput:
    """
    RAG-EVO (v4) — versão funcional e integrável ao kit, sem OO.

    Componentes:
      - Recuperação com diversidade (MMR) se você passar um `mmr_retriever` em inp["extra"]
        (ou usa o retriever padrão)
      - Geração
      - Heurística de confiança composta:
          confidence = alpha*len + beta*entropy + gamma*coverage
      - Fallback iterativo (*iterative recovery*) com gap-query
      - Logging JSONL (auditoria) por round

    extra:
      - rounds: int (default 2)
      - confidence_threshold: float (default 0.6)
      - alpha,beta,gamma: pesos da confiança (default ~1/3 cada)
      - confidence_target_chars: int (default 800)
      - mmr_retriever: callable(query,k,filters)->docs  (opcional)
      - log_dir: str (default "logs")
      - feedback: str|None
      - confidence_mode: "composite" | "llm" | "heuristic"  (default "composite")
    """
    q = inp["query"]
    k = _get(inp, "k", 8)
    filters = _get(inp, "filters", None)
    maxc = _get(inp, "max_context_chars", 12000)

    extra = inp.get("extra", {}) or {}
    rounds = int(extra.get("rounds", 2))
    threshold = float(extra.get("confidence_threshold", 0.6))
    alpha = float(extra.get("alpha", 0.34))
    beta  = float(extra.get("beta", 0.33))
    gamma = float(extra.get("gamma", 0.33))
    target_chars = int(extra.get("confidence_target_chars", 800))
    log_dir = str(extra.get("log_dir", "logs"))
    feedback = extra.get("feedback", None)
    confidence_mode = str(extra.get("confidence_mode", "composite")).lower()

    mmr_retriever = extra.get("mmr_retriever", None)

    pool: Dict[str, Doc] = {}
    cur_query = q

    best_answer = ""
    best_conf = -1.0
    best_docs: List[Doc] = []
    traces = []

    for r in range(max(1, rounds)):
        # retrieve (prefer MMR retriever if provided)
        if callable(mmr_retriever):
            docs = mmr_retriever(cur_query, k * 2, filters)
        else:
            docs = inp["retriever"](cur_query, k * 2, filters)

        for d in docs:
            pool[str(d.get("id"))] = d

        merged = list(pool.values())
        if inp.get("reranker"):
            merged = inp["reranker"](q, merged, k)
        else:
            merged.sort(key=lambda x: x.get("score", 0), reverse=True)
            merged = merged[:k]

        ctx = format_context(merged, maxc)
        answer = inp["llm"](prompt_answer_only_from_context(q, ctx))

        # confidence
        if confidence_mode == "llm":
            conf = llm_confidence(inp["llm"], query=q, answer=answer, context=ctx)
        elif confidence_mode == "heuristic":
            conf = heuristic_confidence(answer)
        else:
            conf = confidence_score(answer, merged, alpha=alpha, beta=beta, gamma=gamma, target_chars=target_chars)

        # log
        log_rag_evo(
            query=q,
            answer=answer,
            confidence=conf,
            diagnostics={
                "algo": "rag_evo_v4",
                "round": r + 1,
                "rounds": rounds,
                "cur_query": cur_query,
                "k": k,
                "confidence_mode": confidence_mode,
                "threshold": threshold,
                "alpha": alpha, "beta": beta, "gamma": gamma,
            },
            feedback=feedback,
            log_dir=log_dir,
        )

        traces.append({
            "round": r + 1,
            "cur_query": cur_query,
            "confidence": conf,
        })

        if conf > best_conf:
            best_conf = conf
            best_answer = answer
            best_docs = merged

        if conf >= threshold:
            break

        # recovery: gerar nova query para buscar lacunas
        cur_query = (inp["llm"](prompt_gap_query(q, answer)).strip() or q)

    return {
        "answer": best_answer,
        "contexts": best_docs,
        "citations": [
            {"doc_id": d.get("doc_id"), "chunk_id": d.get("chunk_id"), "source_path": d.get("source_path")}
            for d in best_docs
        ],
        "diagnostics": {"algo": "rag_evo_v4", "best_conf": best_conf, "traces": traces},
    }
