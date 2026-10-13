from typing import List, Dict, Any, Callable, Optional
from pathlib import Path
import json
import duckdb

from .chunking import split_markdown_to_chunks, build_chunk_docs

Doc = Dict[str, Any]
Embedder = Callable[[str], List[float]]

def upsert_chunks(
    con: duckdb.DuckDBPyConnection,
    *,
    doc_id: str,
    source_path: str,
    chunk_docs: List[Doc],
    embed_fn: Embedder,
) -> int:
    """
    Insere/atualiza chunks na tabela docs.
    """
    inserted = 0
    for cd in chunk_docs:
        chunk_id = int(cd["chunk_id"])
        text = cd["text"]
        meta = cd.get("meta", {})
        emb = embed_fn(text)

        con.execute(
            """
            INSERT INTO docs (doc_id, chunk_id, source_path, text, meta_json, embedding)
            VALUES (?, ?, ?, ?, ?::JSON, ?)
            ON CONFLICT (doc_id, chunk_id)
            DO UPDATE SET
              source_path = excluded.source_path,
              text = excluded.text,
              meta_json = excluded.meta_json,
              embedding = excluded.embedding;
            """,
            [doc_id, chunk_id, source_path, text, json.dumps(meta, ensure_ascii=False), emb]
        )
        inserted += 1
    return inserted

def index_markdown_files(
    con: duckdb.DuckDBPyConnection,
    *,
    md_files: List[str],
    embed_fn: Embedder,
    max_chars: int = 1500,
    overlap: int = 150,
) -> int:
    total = 0
    for md_path in md_files:
        p = Path(md_path)
        doc_id = p.stem
        md = p.read_text(encoding="utf-8")

        chunks = split_markdown_to_chunks(md, max_chars=max_chars, overlap=overlap)
        chunk_docs = build_chunk_docs(chunks, source_id=doc_id, extra_meta={"markdown_path": str(p)})
        total += upsert_chunks(con, doc_id=doc_id, source_path=str(p), chunk_docs=chunk_docs, embed_fn=embed_fn)
    return total
