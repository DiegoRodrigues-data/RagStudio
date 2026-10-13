from typing import Any, Dict, List, Optional, Callable
import duckdb
import numpy as np
import json

Doc = Dict[str, Any]
Embedder = Callable[[str], List[float]]

def safe_json(x: Any) -> Dict[str, Any]:
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    try:
        return json.loads(x)
    except Exception:
        return {"raw": x}

def normalize_scores(xs: List[float]) -> List[float]:
    if not xs:
        return xs
    mn, mx = min(xs), max(xs)
    if mx - mn < 1e-12:
        return [1.0 for _ in xs]
    return [(x - mn) / (mx - mn) for x in xs]

def duckdb_fts_bm25(con: duckdb.DuckDBPyConnection, query: str, k: int) -> List[Doc]:
    """
    Requer PRAGMA create_fts_index('docs','doc_id','text').
    O create_fts_index cria macros de match BM25.
    """
    q = """
        SELECT doc_id, chunk_id, source_path, text, meta_json,
               match_bm25(doc_id, ?) AS score_fts
        FROM docs
        WHERE score_fts IS NOT NULL
        ORDER BY score_fts DESC
        LIMIT ?;
    """
    rows = con.execute(q, [query, k]).fetchall()
    out: List[Doc] = []
    for doc_id, chunk_id, source_path, text, meta_json, score_fts in rows:
        out.append({
            "id": f"{doc_id}:{chunk_id}",
            "doc_id": doc_id,
            "chunk_id": int(chunk_id),
            "source_path": source_path,
            "text": text,
            "meta": safe_json(meta_json),
            "score_fts": float(score_fts),
        })
    return out

def duckdb_like_fallback(con: duckdb.DuckDBPyConnection, query: str, k: int) -> List[Doc]:
    q = """
        SELECT doc_id, chunk_id, source_path, text, meta_json, 1.0 AS score_fts
        FROM docs
        WHERE text ILIKE '%' || ? || '%'
        LIMIT ?;
    """
    rows = con.execute(q, [query, k]).fetchall()
    out: List[Doc] = []
    for doc_id, chunk_id, source_path, text, meta_json, score_fts in rows:
        out.append({
            "id": f"{doc_id}:{chunk_id}",
            "doc_id": doc_id,
            "chunk_id": int(chunk_id),
            "source_path": source_path,
            "text": text,
            "meta": safe_json(meta_json),
            "score_fts": float(score_fts),
        })
    return out

def duckdb_vector_sql(con: duckdb.DuckDBPyConnection, query_emb: List[float], k: int) -> List[Doc]:
    """
    Vetor via SQL com `array_distance` (melhor com extensão vss e índice HNSW).
    Score retornado como -dist (quanto maior, melhor).
    """
    dim = len(query_emb)
    q = f"""
        SELECT doc_id, chunk_id, source_path, text, meta_json,
               -array_distance(embedding, ?::FLOAT[{dim}]) AS score_vec
        FROM docs
        WHERE embedding IS NOT NULL
        ORDER BY array_distance(embedding, ?::FLOAT[{dim}]) ASC
        LIMIT ?;
    """
    rows = con.execute(q, [query_emb, query_emb, k]).fetchall()
    out: List[Doc] = []
    for doc_id, chunk_id, source_path, text, meta_json, score_vec in rows:
        out.append({
            "id": f"{doc_id}:{chunk_id}",
            "doc_id": doc_id,
            "chunk_id": int(chunk_id),
            "source_path": source_path,
            "text": text,
            "meta": safe_json(meta_json),
            "score_vec": float(score_vec),
        })
    return out

def make_duckdb_hybrid_retriever(
    con: duckdb.DuckDBPyConnection,
    *,
    embed_fn: Embedder,
    alpha: float = 0.5,
    use_fts: bool = True,
    use_vector: bool = True,
    prefer_fts_macro: bool = True,
):
    """
    Retriever híbrido: FTS + vetor.
    - FTS: tenta match_bm25 (se create_fts_index foi executado), senão cai no ILIKE.
    - Vetor: usa array_distance em SQL (melhor com vss), sem OO.
    """
    def retriever(query: str, k: int, filters: Optional[Dict[str, Any]] = None) -> List[Doc]:
        pool: Dict[str, Doc] = {}

        # FTS
        fts_docs: List[Doc] = []
        if use_fts:
            if prefer_fts_macro:
                try:
                    fts_docs = duckdb_fts_bm25(con, query, max(k * 4, 20))
                except Exception:
                    fts_docs = duckdb_like_fallback(con, query, max(k * 4, 20))
            else:
                fts_docs = duckdb_like_fallback(con, query, max(k * 4, 20))

        # Vetor
        vec_docs: List[Doc] = []
        if use_vector:
            q_emb = embed_fn(query)
            try:
                vec_docs = duckdb_vector_sql(con, q_emb, max(k * 4, 20))
            except Exception:
                # fallback: se array_distance não existir, sem vetor
                vec_docs = []

        for d in fts_docs:
            pool[str(d["id"])] = d
        for d in vec_docs:
            did = str(d["id"])
            if did in pool:
                pool[did].update(d)
            else:
                pool[did] = d

        merged = list(pool.values())
        s_fts = normalize_scores([d.get("score_fts", 0.0) for d in merged])
        s_vec = normalize_scores([d.get("score_vec", 0.0) for d in merged])

        for i, d in enumerate(merged):
            d["score"] = alpha * s_fts[i] + (1.0 - alpha) * s_vec[i]

        merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return merged[:k]

    return retriever


def duckdb_vector_candidates_with_emb(con: duckdb.DuckDBPyConnection, query_emb: List[float], k: int) -> List[Doc]:
    """
    Retorna candidatos por distância vetorial incluindo o embedding.
    Requer que a tabela docs tenha embedding FLOAT[dim].
    """
    dim = len(query_emb)
    q = f"""
        SELECT doc_id, chunk_id, source_path, text, meta_json, embedding,
               -array_distance(embedding, ?::FLOAT[{dim}]) AS score_vec
        FROM docs
        WHERE embedding IS NOT NULL
        ORDER BY array_distance(embedding, ?::FLOAT[{dim}]) ASC
        LIMIT ?;
    """
    rows = con.execute(q, [query_emb, query_emb, k]).fetchall()
    out: List[Doc] = []
    for doc_id, chunk_id, source_path, text, meta_json, emb, score_vec in rows:
        out.append({
            "id": f"{doc_id}:{chunk_id}",
            "doc_id": doc_id,
            "chunk_id": int(chunk_id),
            "source_path": source_path,
            "text": text,
            "meta": safe_json(meta_json),
            "embedding": emb,
            "score_vec": float(score_vec),
        })
    return out


def make_duckdb_vector_mmr_retriever(
    con: duckdb.DuckDBPyConnection,
    *,
    embed_fn: Embedder,
    k_candidates: int = 40,
    lambda_: float = 0.5,
):
    """
    Retriever vetorial com MMR (diversidade):
      1) busca k_candidates por vetor
      2) seleciona k por MMR (cosine) em Python

    Retorna: retriever(query, k, filters) -> docs
    """
    from .mmr import mmr_select

    def retriever(query: str, k: int, filters: Optional[Dict[str, Any]] = None) -> List[Doc]:
        q_emb = embed_fn(query)
        cand = duckdb_vector_candidates_with_emb(con, q_emb, max(k_candidates, k*4))
        if not cand:
            return []

        doc_embs = [list(d.get("embedding") or []) for d in cand]
        idx = mmr_select(q_emb, doc_embs, k=min(k, len(cand)), lambda_=lambda_)
        out = []
        for i in idx:
            d = dict(cand[i])
            # remove embedding from payload by default (keep lightweight)
            d.pop("embedding", None)
            out.append(d)
        return out

    return retriever
