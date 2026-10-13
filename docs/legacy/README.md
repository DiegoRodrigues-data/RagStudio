# Código legado

`ragkit/` é a biblioteca funcional de onde vieram os sete algoritmos iniciais do RagStudio. Está arquivada aqui,
sem alterações, apenas como referência de origem. Não é importada por nenhum módulo e não é coberta por testes ou lint.

| Função original (`ragkit/ragkit/rag_algorithms.py`) | Técnica no RagStudio |
|---|---|
| `rag_naive` | `ragstudio/techniques/naive.py` |
| `rag_hyde` | `ragstudio/techniques/hyde.py` |
| `rag_multi_query` | `ragstudio/techniques/multi_query.py` |
| `rag_decomposition` | `ragstudio/techniques/decomposition.py` |
| `rag_iterative` | `ragstudio/techniques/iterative.py` |
| `rag_context_compression` | `ragstudio/techniques/context_compression.py` |
| `rag_evo` + `evo_heuristics.py` + `evo_utils.py` | `ragstudio/techniques/rag_evo/` |
| `mmr.py`, `make_duckdb_vector_mmr_retriever` | `ragstudio/retrieval/mmr.py`, `ragstudio/techniques/mmr_rag.py` |
| `duckdb_schema.py`, `duckdb_store.py` | `ragstudio/stores/duckdb.py`, `ragstudio/retrieval/hybrid.py` |
| `rerankers.py` | `ragstudio/rerankers/llm.py` |
| `prompts.py` | `ragstudio/prompts/templates.py` |
| `chunking.py`, `ingest_docling.py` | `ragstudio/processing/chunking/fixed.py`, `ragstudio/ingest/loaders/pdf_docling.py` |
| `llm_providers.py`, `embed_providers.py` | `ragstudio/providers/` |
