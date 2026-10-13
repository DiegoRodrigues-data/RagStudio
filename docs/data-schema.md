# Dados e esquema

## Onde fica cada coisa

| Local | Conteúdo |
|---|---|
| `Dados/ragstudio.sqlite` | tudo que é estruturado: corpora, documentos, perguntas, runbooks, runs, resultados, métricas, evidências |
| `Dados/indices/<index_hash>/` | `meta.json`, `chunks.jsonl`, `embeddings.npy`, `documents.jsonl`, `index_texts.jsonl`, `aux_*.json`, e `index.duckdb` no store DuckDB, `index.faiss` no store FAISS, `chroma/` no store Chroma |
| `Dados/indices/_embedding_cache.sqlite` | cache de embeddings por provider, modelo e hash do texto |
| `Dados/runs/<run_id>/results.jsonl` | uma linha por pergunta com o resultado completo da técnica |
| `Dados/exports/`, `Dados/figures/` | tabelas, relatórios e figuras |
| `Dados/backups/` | cópias do banco, manuais e automáticas (as 10 últimas) |
| `ragstudio/config/config.local.ini` | configuração local, inclusive a chave de API; fora do git |

Variáveis de ambiente: `RAGSTUDIO_DATA_DIR`, `RAGSTUDIO_DB`, `RAGSTUDIO_CONFIG`, `RAGSTUDIO_PROVIDER`,
`RAGSTUDIO_<SEÇÃO>_<CHAVE>`, `RAGSTUDIO_TECHNIQUES_PATH`, `RAGSTUDIO_PYTHON`, `RAGSTUDIO_LOG_LEVEL`.

Por que SQLite para resultados e arquivos para índices: resultados precisam de integridade referencial, triggers de
imutabilidade e cadeia de hashes; índices são matrizes grandes, regeneráveis e identificadas por hash.

## Tabelas

| Tabela | Uma linha por | Colunas principais |
|---|---|---|
| `corpora` | corpus | `name`, `content_hash`, `profile` (JSON), `cleaning` |
| `documents` | documento | `corpus_id`, `doc_id`, `sha256`, `format`, `language`, `chars`, `text`, `metadata`, `profile` |
| `corpus_splits` | corpus × split | `document_ids`, `split_hash`, `seed` |
| `indices` | índice | `index_hash`, `chunking`, `embedding_model`, `store`, `enrich`, `dim`, `chunks`, `chunking_profile`, `build_usage` |
| `question_sets`, `questions`, `gold_passages` | conjunto, pergunta, trecho gold | `code`, `text`, `expected_answer`, `answer_type`, `split`, `version`, `supersedes_id`, `archived_at`; `char_start`, `char_end` |
| `runbooks` | runbook | `config` (grade normalizada), `status`, `max_budget_usd`, `estimate` |
| `runs` | run | `technique`, `technique_version`, `config`, `config_hash`, `index_hash`, `status`, `error`, `cost_usd`, `replicates_run_id` |
| `query_results` | run × pergunta | `answer`, `context_text`, `citations`, `diagnostics`, `timings`, `usage`, `latency_total`, `llm_calls`, tokens, `cost_usd`, `warnings`, `error` |
| `retrieved_chunks` | resultado × rank | `chunk_id`, `document_id`, `score`, `source`, offsets, `in_context`, `text` |
| `retrieval_metrics` | resultado × versão de avaliação | `k`, `gold_count`, `hit`, `recall`, `precision`, `mrr`, `ndcg`, `context_coverage` |
| `generation_metrics` | resultado × versão de avaliação | `exact_match`, `f1`, `accuracy`, `faithfulness`, `groundedness`, `citation_accuracy`, `hallucination`, `refusal`, `judge_*` |
| `run_metrics` | run × versão de avaliação | `metrics` (agregados), `availability` |
| `evidence_events` | evento | `seq`, `kind`, `payload`, `payload_sha256`, `prev_sha256`, `chain_sha256` |
| `prompts` | template | `sha256`, `task`, `language`, `system`, `template`, `version` |
| `environment_snapshots` | run | versões de Python e pacotes, plataforma, commit, LLM, embedder, seed |
| `exports` | arquivo exportado | `kind`, `ref`, `format`, `path`, `sha256` |
| `answer_reviews` | revisão humana | `reviewer`, `verdict`, `note` |

## Regras

- **Imutabilidade.** Triggers rejeitam `UPDATE` e `DELETE` em `query_results`, `retrieved_chunks` e
  `evidence_events` de runs concluídos, e a reconfiguração de um run concluído. `evidence_events` nunca aceita
  `UPDATE`. A única remoção possível é `experiments delete --confirm "<nome exato>"`, que faz backup antes.
- **Cadeia de evidências.** `chain = sha256(chain_anterior + sha256(payload canônico))`. `experiments verify`
  recalcula tudo e aponta o `seq` quebrado. Detecta edição e remoção de eventos.
- **Métricas são append-only.** Reavaliar grava uma nova `eval_version`. As consultas usam a mais recente.
- **Perguntas versionadas.** Editar pergunta usada por run concluído cria nova versão e arquiva a anterior.
- **Índice usado por run concluído não pode ser apagado.**
- **Migrações.** Mudança de esquema é um novo arquivo em `ragstudio/db/migrations/`. Nunca edite uma migração aplicada.

## Evidência por pergunta

Na ordem: `retrieval` (consulta, modo, k, ids e scores), `request` (tarefa, hash do prompt, texto enviado, modelo,
temperatura, seed), `response` (texto, tokens, latência, fingerprint), `retry` e `error` quando ocorrem, e
`evaluation` (métricas). Cada run começa e termina com um evento `info`.

## Artefato JSONL

`{"query_result_id", "question", "result": {answer, contexts, context, citations, diagnostics, timings, usage,
warnings}, "latency_total", "cost_usd", "error", "metrics"}`. O SHA-256 do arquivo fica em `exports` e no evento
final do run.

## Tabelas exportadas

`./rs reports schema` descreve as colunas de `runs`, `questions` e `characteristics`. Célula vazia significa que a
métrica não pôde ser medida.
