from typing import Optional
import duckdb

def init_db(con: duckdb.DuckDBPyConnection, *, embedding_dim: int) -> None:
    """
    Cria tabela 'docs' com embedding em ARRAY fixo (necessário para vss/HNSW).
    """
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS docs (
            doc_id VARCHAR,
            chunk_id INTEGER,
            source_path VARCHAR,
            text TEXT,
            meta_json JSON,
            embedding FLOAT[{embedding_dim}],
            PRIMARY KEY (doc_id, chunk_id)
        );
    """)

def ensure_extensions(con: duckdb.DuckDBPyConnection, *, use_fts: bool = True, use_vss: bool = True) -> None:
    """
    Instala/carrega extensões do DuckDB quando disponíveis.
    """
    if use_fts:
        con.execute("INSTALL fts;")
        con.execute("LOAD fts;")
    if use_vss:
        con.execute("INSTALL vss;")
        con.execute("LOAD vss;")

def build_fts_index(con: duckdb.DuckDBPyConnection) -> None:
    """
    Cria índice FTS para docs.text (requer extensão fts).
    """
    con.execute("PRAGMA create_fts_index('docs', 'doc_id', 'text');")

def build_vss_index(con: duckdb.DuckDBPyConnection) -> None:
    """
    Cria índice HNSW para embeddings (requer extensão vss).
    """
    con.execute("CREATE INDEX IF NOT EXISTS docs_hnsw ON docs USING HNSW(embedding);")
