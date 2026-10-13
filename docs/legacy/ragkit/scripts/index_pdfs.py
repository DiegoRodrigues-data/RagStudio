import argparse
import os
import duckdb

from ragkit.embed_providers import make_embed_lmstudio, make_embed_openai
from ragkit.ingest_docling import convert_pdfs_to_markdown
from ragkit.duckdb_schema import init_db, ensure_extensions, build_fts_index, build_vss_index
from ragkit.indexer import index_markdown_files

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="rag.duckdb")
    p.add_argument("--out_md", default="out_markdown")
    p.add_argument("--embedding_dim", type=int, default=768)

    p.add_argument("--embed_provider", choices=["lmstudio","openai"], default="lmstudio")
    p.add_argument("--embed_model", required=True)
    p.add_argument("--lmstudio_base", default="http://localhost:1234")
    p.add_argument("--openai_key", default=os.environ.get("OPENAI_API_KEY",""))

    p.add_argument("--build_fts", action="store_true")
    p.add_argument("--build_vss", action="store_true")

    p.add_argument("--max_chars", type=int, default=1500)
    p.add_argument("--overlap", type=int, default=150)

    p.add_argument("pdfs", nargs="+")
    return p.parse_args()

def main():
    a = parse_args()

    con = duckdb.connect(a.db)
    init_db(con, embedding_dim=a.embedding_dim)

    # extensões (opcional, mas recomendado)
    if a.build_fts or a.build_vss:
        ensure_extensions(con, use_fts=a.build_fts, use_vss=a.build_vss)
        if a.build_fts:
            build_fts_index(con)
        if a.build_vss:
            build_vss_index(con)

    if a.embed_provider == "lmstudio":
        embed_fn = make_embed_lmstudio(a.lmstudio_base, a.embed_model)
    else:
        if not a.openai_key:
            raise SystemExit("OPENAI_API_KEY não definido (ou passe --openai_key)")
        embed_fn = make_embed_openai(a.openai_key, a.embed_model)

    conv = convert_pdfs_to_markdown(a.pdfs, output_dir=a.out_md)
    md_files = [c["markdown_path"] for c in conv]

    total = index_markdown_files(
        con,
        md_files=md_files,
        embed_fn=embed_fn,
        max_chars=a.max_chars,
        overlap=a.overlap,
    )
    print(f"OK: {total} chunks indexados em {a.db}")

if __name__ == "__main__":
    main()
