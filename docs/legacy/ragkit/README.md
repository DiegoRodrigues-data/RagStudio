# RAG Kit v2 — PDF -> Markdown (Docling) -> DuckDB (FTS + Vetor) -> LLM (LM Studio / OpenAI)

Este projeto é **100% funções e módulos** (sem orientação a objetos).

## Fluxo (indexação)
1) PDFs entram no pipeline
2) Docling converte cada PDF para Markdown (arquivo .md por PDF)
3) Chunking do Markdown (ex.: 1500 chars, overlap 150)
4) Para cada chunk:
   - gera embedding (LM Studio ou OpenAI)
   - insere em `docs(doc_id, chunk_id, text, meta_json, embedding)`
5) Índices (opcional, mas recomendado):
   - FTS: `INSTALL fts; LOAD fts; PRAGMA create_fts_index('docs','doc_id','text');`
   - Vetor: `INSTALL vss; LOAD vss; CREATE INDEX ... USING HNSW(embedding);`

## Dependências
- Python 3.10+
- duckdb
- numpy
- requests
- docling

## Indexar PDFs (CLI)
Exemplo com LM Studio para embeddings:

```bash
python scripts/index_pdfs.py \
  --db rag.duckdb \
  --out_md out_markdown \
  --embedding_dim 768 \
  --embed_provider lmstudio \
  --embed_model text-embedding-model \
  --lmstudio_base http://localhost:1234 \
  --build_fts --build_vss \
  ./meus_pdfs/*.pdf
```

## Rodar pergunta (RAG)
Depois de indexar, rode:

```bash
python main.py
```

> Ajuste `main.py` para seu modelo de chat no LM Studio ou OpenAI.


## Técnica adicional: RAG-EVO (MVP)
- Implementada como `rag_evo(inp)` em `ragkit/rag_algorithms.py`.
- Faz rounds de recuperação com *iterative recovery* e registra logs JSONL em `logs/rag_evo_log.jsonl`.
- Configurações via `inp['extra']`: `rounds`, `confidence_mode`, `confidence_threshold`, `log_dir`.
## RAG-EVO v4 (com MMR + confiança composta)
- `rag_evo(inp)` agora suporta:
  - Recuperação com diversidade via **MMR** (opcional, passando `mmr_retriever` em `inp["extra"]`)
  - Confiança composta: `alpha*len + beta*entropy + gamma*coverage`
  - Fallback iterativo com gap-query
  - Log JSONL por round em `logs/rag_evo_log.jsonl`

### Exemplo de MMR retriever (vetorial)
Você pode criar um retriever MMR e injetar em `extra`:

```python
from ragkit.duckdb_store import make_duckdb_vector_mmr_retriever

mmr_retriever = make_duckdb_vector_mmr_retriever(
    con,
    embed_fn=embed_fn,
    k_candidates=40,
    lambda_=0.6,
)

out = rag_evo({
  **inp,
  "extra": {**inp.get("extra", {}), "mmr_retriever": mmr_retriever, "confidence_mode": "composite"}
})
```
