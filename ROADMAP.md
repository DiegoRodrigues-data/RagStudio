# ROADMAP — RagStudio

Acompanhamento da implementação completa e funcional do projeto.
Marque cada item conforme for concluído: `[ ]` → `[x]`.

**Legenda de status das fases:** ⬜ Não iniciada · 🟡 Em andamento · ✅ Concluída

---

## Propósito

**RagStudio** é um ambiente único para **implementar, executar, comparar e validar técnicas RAG** (Retrieval-Augmented Generation) de forma reproduzível. Toda técnica obedece ao mesmo fluxo e ao mesmo contrato:

```
documento → carregamento/normalização → chunking → índice → recuperação → (rerank / expansão / compressão) → contexto → geração → resultado → avaliação
```

O produto do RagStudio não é a resposta de uma pergunta, mas o **conjunto de dados comparáveis** (métricas de recuperação, métricas de geração, latência por etapa, tokens, custo, contexto enviado, fontes) gerado ao rodar as mesmas perguntas, sobre o mesmo corpus, com técnicas diferentes. Esses dados alimentam uma análise empírica que cruza desempenho com **características do corpus e dos documentos** (quantidade, tamanho, tipo de arquivo, idioma, tamanho e número de chunks).

### Material de referência deste roadmap

| Fonte | O que foi aproveitado |
|---|---|
| `20261012_110145_ferramenta-chamada-ragstudio-em-que-implementa-todas-as.md` | Prompt principal: objetivos, fluxo padrão, requisitos de arquitetura, campos a registrar, critérios de aceitação |
| `ragkit/` (1.232 linhas, 100 % funções) | Algoritmos já implementados: `rag_naive`, `rag_hyde`, `rag_multi_query`, `rag_decomposition`, `rag_iterative`, `rag_context_compression`, `rag_evo` (v4 com MMR e confiança composta); retriever híbrido DuckDB (FTS + VSS), retriever vetorial com MMR, rerank LLM, providers LM Studio/OpenAI, ingestão Docling, chunking de Markdown |
| ` Técnicas de RAG Implementadas no Projeto.md` e `Artigo.pdf` (mesmo conteúdo em PDF) | Fundamentação acadêmica de 6 técnicas: Naive RAG (Lewis 2020), HyDE (Gao 2023), MMR (Carbonell 1998), Iterative/FLARE, RAG-EVO (Springer), Multi-Query (survey Gupta 2024); survey Zhao 2024 |
| `../JudDoc_Ex` (projeto de inspiração) | Layout: CLI Python com contrato JSON (`{"ok":true,"data":…}`), um arquivo por grupo de comandos, `Repo` como único lugar com SQL, migrações numeradas, provider `mock` determinístico para testes offline, `isolated_env` nos testes, ledger de evidências com cadeia de hashes, `environment_snapshots`, `config_hash` por run, relatórios/figuras em inglês, `run.sh` com verificações, `CLAUDE.md`, `DCR/` com lições. Avaliador em níveis 0–3 (latência/custo, recall@k/MRR/nDCG, faithfulness/citação/alucinação, accuracy/EM/F1/juiz) |

---

## Estado atual

*Atualizado em 2026-10-12, depois da construção da interface desktop.*

**Funcional:** aplicação desktop em `Frontend/` (Electron + React 19 + shadcn/ui, 7 telas, cerca de 11.000 linhas fora dos componentes shadcn, parte da casca herdada do JudDoc_Ex) sobre o pacote `ragstudio/` (cerca de 7.900 linhas) com CLI de contrato JSON (`./rs`, 10 grupos), núcleo com contrato de técnica e registry por descoberta, providers mock / OpenAI / LM Studio / Ollama sobre HTTP puro, ingestão (md, txt, json, jsonl) com perfil de corpus e splits, 4 estratégias de chunking, índice em memória e DuckDB identificados por hash, 5 modos de recuperação, 3 rerankers, **16 técnicas registradas** (13 `implemented`, 3 `prototype`), executor de runbooks com retomada, orçamento e réplicas, SQLite com imutabilidade e cadeia de evidências, avaliação de recuperação e geração com juiz opcional, comparação pareada com estatística, análise por características dos documentos, exportações CSV/JSON/Parquet, figuras e relatório HTML. Documentação em `README.md`, `docs/`, `CLAUDE.md` e `DCR/`.

**Verificado:** o Frontend passa em typecheck, lint e build, e todas as telas foram conferidas por screenshot do app rodando contra um banco de teste, incluindo um runbook de 16 runs criado e executado pela interface. No backend, 343 testes passam e 3 são pulados de propósito (provider real), em 6,3 s, com `ruff` limpo (`scripts/check.sh`). O fluxo completo foi exercitado pela CLI em diretório de teste: importação, runbook de 40 runs, comparação, relatório HTML com 9 figuras, exportação Parquet, verificação da cadeia. O cliente HTTP foi testado contra um servidor falso compatível com OpenAI, incluindo um runbook inteiro. `./run.sh --demo` foi executado até o fim.

**Não verificado / pendente:**
- **Primeira execução real feita pelo usuário em 2026-10-12** (OpenAI, `gpt-4o-mini`, store `chroma`, 1 pergunta sem gold, 1280 runs): 960 concluídos e 320 falharam, todos pela ausência do `sentence-transformers` exigido pelo reranker `cross_encoder`. O pacote foi instalado e o runbook agora recusa dependência faltante antes de executar. Os 320 runs ainda precisam ser reexecutados. A suíte de testes continua sem chamar provider real.
- Loader de PDF via Docling: instalado e exercitado em 2026-10-12 com 3 sentenças reais (cerca de 4 s por documento depois de carregados os modelos); não rodado em lote grande.
- Reranker cross-encoder: exercitado à mão com `sentence-transformers` 5.7.0 e o modelo padrão (treinado em inglês); ainda não rodado dentro de um runbook real nem avaliado em português.
- As 8 técnicas novas (`hybrid_rag`, `rag_fusion`, `multi_hop`, `adaptive_rag`, `self_rag`, `rank_rag`, `light_rag`, `hippo_rag`) e as 3 reescritas (`graph_rag`, `raptor`, `agentic`) só rodaram com o provider simulado. `self_rag` e `rank_rag` são protótipos: os artigos dependem de modelos treinados (ver `docs/techniques.md`).
- Chamada nativa de ferramentas (`agentic`): testada contra o servidor falso compatível com OpenAI, não contra um provider real.
- RAPTOR com UMAP: o pacote `umap-learn` não está instalado; a redução em uso é PCA.
- Índice em memória não foi medido com corpus grande.
- Aplicação desktop: conferida só com o provider simulado; seletor de arquivos nativo, cancelamento de run longo e empacotamento não foram exercitados; sem testes automatizados de interface.

---

## Decisões de arquitetura (premissas deste roadmap)

- **Linguagem e ambiente:** Python 3.11, conda env `ragstudio` (`environment.yml` + `requirements.txt` como fallback), mesmo padrão do JudDoc_Ex. O RagStudio nasceu como **pacote Python + CLI com contrato JSON**; a interface desktop (Fase 11) foi construída depois sobre essa CLI, reaproveitando a ponte Electron → Python do JudDoc_Ex.
- **Estilo de código:** funções pequenas com type hints e `dataclasses` imutáveis (`frozen=True`) para os modelos de dados. Classes só onde um contrato precisa de estado (`Repo`, adaptadores de store). O estilo "100 % funções" do `ragkit` é mantido dentro de cada técnica.
- **Uma técnica = um módulo:** `ragstudio/techniques/<nome>.py` com a função `run(request: TechniqueRequest, deps: TechniqueDeps) -> TechniqueResult` e um `SPEC = TechniqueSpec(...)` (nome, versão, parâmetros, dependências, referência acadêmica, status). Técnicas com componentes próprios viram subpacote `ragstudio/techniques/<nome>/` (ex.: `rag_evo/`, `graph_rag/`). O núcleo nunca importa uma técnica pelo nome; o `registry` descobre os módulos.
- **Dependências injetadas:** a técnica recebe `retriever`, `embedder`, `llm`, `reranker` e `store` já construídos pelo executor a partir da configuração. Nenhuma técnica abre conexão, lê `config.ini` ou escolhe modelo.
- **Dois armazenamentos com papéis distintos:**
  - **Índices** (chunks + embeddings): adaptador `stores/memory.py` (numpy, persistido em `Dados/indices/<hash>/`) como padrão, e `stores/duckdb.py` (FTS + VSS, portado do `ragkit`) como opcional. O hash do índice é `sha256(corpus_id, chunking, embedding_model)`, o que evita recomputar embeddings entre técnicas que compartilham a mesma indexação.
  - **Resultados e evidências**: **SQLite** `Dados/ragstudio.sqlite` (WAL, migrações numeradas, triggers de imutabilidade), seguindo a especificação em `../JudDoc_Ex/DCR/sqlite-ledger-de-evidencias.md`. Motivo: o JudDoc_Ex já validou esse desenho para auditoria e artigos; DuckDB fica restrito a índice porque seu ponto forte é busca, não ledger append-only. Artefatos grandes (contexto final, respostas brutas) ficam em JSONL por run em `Dados/runs/<run_id>/` com SHA-256 registrado no banco; exportação analítica em CSV e Parquet.
- **Reprodutibilidade:** seed global propagada a providers (quando suportam), `config_hash` canônico por run, `environment_snapshot` (versões, SO, commit, provider, URL, modelo, fingerprint do modelo), prompts deduplicados por hash, replay de um run a partir do banco.
- **Testável sem API paga:** provider `mock` determinístico (embedding por bag-of-words hasheado, LLM extrativo) ativado por `RAGSTUDIO_PROVIDER=mock`; todos os testes rodam offline. Variáveis `RAGSTUDIO_DATA_DIR`, `RAGSTUDIO_DB`, `RAGSTUDIO_CONFIG` isolam a árvore de dados.
- **Anti-vazamento:** `corpus_splits` (train/validation/test) definidos por lista de `document_id` com hash; o executor recusa um runbook cujo question set referencie documentos de um split diferente do declarado; few-shot e sugestões de gold só podem vir do split de treino.
- **Sem métrica inventada:** métricas de recuperação exigem gold passages; métricas de acurácia exigem resposta esperada. Sem gold, o run registra `evaluation.available = [...]` e `evaluation.requires_annotation = [...]` em vez de números.
- **Status de cada componente** é declarado no `SPEC` de cada técnica e no catálogo abaixo com um de cinco valores: `implementado` · `protótipo` · `adaptador` · `mock` · `pendente`.
- **Idiomas:** código, identificadores, docstrings e rótulos de relatório em inglês; documentação do projeto (`ROADMAP.md`, `README.md`, `DCR/`) em português; prompts em português quando o corpus for em português (parametrizável por `language`).

---

## Catálogo de técnicas e status

A expressão "todas as técnicas RAG" é tratada como um **catálogo extensível**: cada entrada abaixo nasce como `pendente` e só muda de status quando o módulo existir, tiver teste com provider mock e um `SPEC` honesto.

| Família | Técnica | Módulo | Origem | Status |
|---|---|---|---|---|
| Básica | Naive RAG | `techniques/naive.py` | `ragkit.rag_naive` | implementado |
| Recuperação | Lexical BM25 | `retrieval/bm25.py` (`retrieval_mode: bm25`) | JudDoc_Ex, DuckDB FTS | implementado |
| Recuperação | Híbrida dense + BM25 | `retrieval/hybrid.py` (`retrieval_mode: hybrid`) | `ragkit`, JudDoc_Ex | implementado |
| Recuperação | Híbrida por RRF | `retrieval/fusion.py` (`retrieval_mode: rrf`) | nova | implementado |
| Diversidade | MMR | `retrieval/mmr.py` + `techniques/mmr_rag.py` | `ragkit.mmr` | implementado |
| Consulta | HyDE | `techniques/hyde.py` | `ragkit.rag_hyde` | implementado |
| Consulta | Multi-Query / expansão | `techniques/multi_query.py` | `ragkit.rag_multi_query` | implementado |
| Consulta | Decomposição em subperguntas | `techniques/decomposition.py` | `ragkit.rag_decomposition` | implementado |
| Consulta | Step-back prompting | `techniques/step_back.py` | nova | implementado |
| Iterativa | Iterative / gap-query | `techniques/iterative.py` | `ragkit.rag_iterative` | implementado |
| Iterativa | RAG-EVO v4 | `techniques/rag_evo/` | `ragkit.rag_evo` | implementado |
| Contexto | Contextual compression | `techniques/context_compression.py` | `ragkit.rag_context_compression` | implementado |
| Reranking | Rerank por LLM | `rerankers/llm.py` | `ragkit.make_rerank_llm` | implementado |
| Reranking | Rerank heurístico por termos | `rerankers/lexical.py` | JudDoc_Ex | implementado |
| Reranking | Cross-encoder local | `rerankers/cross_encoder.py` | nova | adaptador (não exercitado) |
| Estrutura | Parent-child | `techniques/parent_child.py` + `processing/chunking/parent_child.py` | nova | implementado |
| Contexto | Long-Context RAG | `techniques/long_context.py` | nova | implementado |
| Estrutura | Hierarchical Retrieval | `techniques/hierarchical.py` | nova | implementado |
| Contexto | RECOMP | `techniques/recomp.py` | nova | protótipo (compressores por prompt e embedding, sem treino) |
| Autoavaliação | Speculative RAG | `techniques/speculative_rag.py` | nova | protótipo (um único LLM rascunha e verifica) |
| Chunking | Recursive e Semantic | `processing/chunking/recursive.py`, `semantic.py` | nova | implementado |
| Estrutura | Sentence window | `techniques/sentence_window.py` | nova | implementado |
| Estrutura | Contextual retrieval | `techniques/contextual_retrieval.py` + `enrich: contextual` | nova | implementado |
| Estrutura | RAPTOR | `techniques/raptor/` | nova | implementado (árvore recursiva, mistura gaussiana suave com BIC; UMAP só com `umap-learn`, senão PCA) |
| Grafo | GraphRAG | `techniques/graph_rag/` + `stores/graph.py` + `techniques/_kg.py` | nova | implementado (relações tipadas, comunidades Louvain, relatórios, busca local e global) |
| Grafo | LightRAG | `techniques/light_rag.py` | nova | implementado (dois níveis, modos local, global, hybrid e mix) |
| Grafo | HippoRAG | `techniques/hippo_rag.py` | nova | implementado (Personalized PageRank, arestas de sinônimo) |
| Autoavaliação | Corrective RAG | `techniques/corrective.py` | nova | implementado, sem busca web |
| Autoavaliação | Self-RAG | `techniques/self_rag.py` | nova | protótipo (reflexões por prompt, sem modelo treinado) |
| Roteamento | Adaptive RAG | `techniques/adaptive_rag.py` | nova | implementado (classificador por prompt) |
| Ranqueamento | RankRAG | `techniques/rank_rag.py` | nova | protótipo (notas por prompt, sem modelo treinado) |
| Iterativa | Multi-Hop RAG | `techniques/multi_hop.py` + `techniques/_multihop.py` | nova | implementado |
| Básica | Hybrid RAG | `techniques/hybrid_rag.py` | nova | implementado |
| Consulta | RAG-Fusion | `techniques/rag_fusion.py` | nova | implementado |
| Agente | Agentic RAG | `techniques/agentic/` | nova | implementado (plano, 4 ferramentas, tool calling nativo com recuo para texto) |
| Store | DuckDB (FTS + vetor) | `stores/duckdb.py` | `ragkit.duckdb_store` | adaptador (testado com DuckDB 1.4.1) |
| Store | FAISS (`IndexFlatIP`, cosseno exato) | `stores/faiss.py` | nova | adaptador (testado com faiss-cpu 1.15.1, só com embeddings do mock) |
| Store | Chroma (HNSW cosseno, aproximado) | `stores/chroma.py` | nova | adaptador (testado com chromadb 1.5.9, só com embeddings do mock) |
| Loader | PDF via Docling | `ingest/loaders/pdf_docling.py` | `ragkit.ingest_docling`, pipeline do JudDoc_Ex | implementado (exercitado com 3 PDFs reais) |

"Implementado" significa código completo no contrato comum, com testes passando no provider mock. As 16 técnicas da primeira versão rodaram com LLM real no experimento do usuário de 2026-10-12, sem anotação que permita validar qualidade; as demais só rodaram com o mock.

Técnicas fora desta tabela entram por pull request com uma nova linha e um novo módulo; nenhuma alteração no núcleo é esperada.

---

## Árvore de diretórios alvo

```
RAG_STUDIO/
├── ragstudio/                      pacote Python (importável como biblioteca)
│   ├── cli.py                      entrypoint: argparse por grupos → contrato JSON
│   ├── cli_groups/                 db · config · corpus · index · techniques · questions · experiments · evaluate · compare · reports
│   ├── config/                     config.ini (defaults) · config.local.ini (git-ignored) · loader.py
│   ├── core/                       models.py (Document, Chunk, Query, RetrievedChunk, Context, Answer, StageTiming, Usage, TechniqueRequest/Result)
│   │                               contract.py (TechniqueSpec, TechniqueDeps, protocolo run) · registry.py · errors.py · seeds.py · timing.py · logging.py · hashing.py
│   ├── providers/                  base.py · openai.py · lmstudio.py · ollama.py · mock.py · routing.py · pricing.json · fingerprint.py
│   ├── ingest/                     loaders/ (markdown, text, pdf_docling lazy) · cleaner.py · profile.py (características do corpus) · splits.py
│   ├── processing/                 chunking/ (fixed, markdown_headers, sentence, parent_child) · normalize.py
│   ├── stores/                     base.py · memory.py · duckdb.py · faiss.py · chroma.py · graph.py (adaptador)
│   ├── retrieval/                  dense.py · bm25.py · hybrid.py · fusion.py · mmr.py
│   ├── rerankers/                  noop.py · lexical.py · llm.py · cross_encoder.py
│   ├── prompts/                    templates versionados por idioma (pt, en) + registry por hash
│   ├── techniques/                 um .py por técnica ou subpacote quando houver componentes próprios
│   ├── experiments/                runbook.py (grade) · runner.py · artifacts.py (JSONL por run) · cost.py
│   ├── evaluation/                 retrieval_metrics.py · generation_metrics.py · judge.py · availability.py
│   ├── analysis/                   compare.py · stats.py · characteristics.py · exports.py (CSV/Parquet/JSON)
│   ├── reports/                    style.py · charts.py · tables.py · html_report.py
│   └── db/                         connection.py · migrate.py · migrations/NNNN_*.sql · repository.py · backup.py
├── configs/                        exemplos de runbook (YAML/JSON) e de config por provider
├── Dados/                          Input/ (originais) · Output/ (Markdown) · indices/ · runs/ · exports/ · figures/ · backups/ · ragstudio.sqlite
├── tests/                          pytest offline (provider mock), fixtures com corpus pequeno em Markdown
├── docs/                           como executar · como comparar · como adicionar uma técnica · referências acadêmicas
├── run.sh                          bootstrap do ambiente (conda → deps → migração → provider), na raiz
├── scripts/                        check.sh (ruff + pytest)
├── docs/legacy/ragkit/             fonte dos algoritmos portados, arquivada sem alterações
├── DCR/                            lições reaproveitáveis
├── rs                              lançador da CLI
├── Frontend/                       aplicação desktop (Electron + Vite + React + shadcn/ui)
├── CLAUDE.md · README.md · ROADMAP.md · environment.yml · requirements.txt · pyproject.toml
```

---

> **Nota sobre nomes de arquivos.** Alguns itens abaixo citam os nomes planejados. Na implementação, os testes foram consolidados em menos arquivos (`tests/test_core.py`, `test_providers.py`, `test_ingest.py`, `test_chunking.py`, `test_stores_retrieval.py`, `test_db.py`, `test_runbook_runner.py`, `test_evaluation.py`, `test_analysis_reports.py`, `test_http_provider.py`, `tests/techniques/`), a revisão humana ficou em `evaluation/service.py` e a agregação em `evaluation/aggregate.py`. O conteúdo de cada item foi entregue; a árvore real está no `README.md`.

## Fase 0 — Fundação do projeto ✅
Sem pacote, ambiente, contrato de CLI e testes offline nenhuma técnica pode ser verificada.

- [x] Criar árvore: `ragstudio/` (com `__init__.py` em cada subpacote), `configs/`, `Dados/{Input,Output,indices,runs,exports,figures,backups}`, `tests/fixtures/`, `docs/`, `scripts/`
- [x] `environment.yml` (conda env `ragstudio`, Python 3.11, versões fixas: `numpy`, `duckdb`, `requests`, `pyyaml`, `rank-bm25`, `pandas`, `pyarrow`, `matplotlib`, `jinja2`, `pytest`, `ruff`; `docling` e `sentence-transformers` como extras opcionais) e `requirements.txt`
- [x] `pyproject.toml` com `[project.scripts] ragstudio = "ragstudio.cli:main"`, configuração do `ruff` (line-length, regras) e do `pytest` (`testpaths`, variáveis de isolamento)
- [x] `ragstudio/cli.py`: argparse por grupos → `cli_groups/<grupo>_cmd.py`; toda saída é **uma linha JSON final** `{"ok":true,"data":…}` ou `{"ok":false,"error":…,"warnings":[…]}`; `--stream` emite linhas JSON de progresso antes; logging estruturado em stderr (portar padrão de `../JudDoc_Ex/Backend/juddoc.py` e `cli/common.py`)
- [x] `ragstudio/config/`: `config.ini` com seções `[openai]`, `[lm_studio]`, `[ollama]`, `[embedding]`, `[llm]`, `[experiments]`, `[evaluation]`, `[paths]`; `config.local.ini` git-ignored; `loader.py` com roteamento por provider (portar `resolve_endpoints` e `_normalize_local_base` do JudDoc_Ex) e sobrescrita por `RAGSTUDIO_*`
- [x] `ragstudio/core/paths.py`: diretórios resolvidos a partir de `RAGSTUDIO_DATA_DIR`, `RAGSTUDIO_DB`, `RAGSTUDIO_CONFIG`; nenhum módulo copia constantes no import (pitfall documentado no JudDoc_Ex)
- [x] `tests/conftest.py`: fixture `isolated_env` (árvore temporária + `RAGSTUDIO_PROVIDER=mock`) e fixture `small_corpus` (3 documentos Markdown curtos em pt-BR com perguntas e gold passages em `tests/fixtures/`)
- [x] `scripts/check.sh` (ruff + pytest) e `./run.sh` (conda env → deps → `db migrate`)
- [x] `.gitignore` (`Dados/*.sqlite*`, `Dados/indices`, `Dados/runs`, `config.local.ini`, caches), `git init`, primeiro commit; lançador `./rs` (zsh não divide `$PY -m ragstudio`)
- [x] `CLAUDE.md` inicial: comandos, arquitetura, contrato JSON, regra "uma técnica = um módulo", variáveis de isolamento
- [x] Teste `tests/test_cli_contract.py`: comando desconhecido e erro de handler produzem `{"ok":false}` com exit code ≠ 0; `help` lista os grupos

## Fase 1 — Núcleo: modelos de dados, contrato de técnica e registry ✅
É o que torna todas as técnicas compatíveis entre si; tudo o que vem depois depende destes tipos.

- [x] `core/models.py` com `dataclasses(frozen=True)` e `to_dict()`: `Document(id, source_path, sha256, text, format, language, chars, pages, metadata)`, `Chunk(id, document_id, index, text, char_start, char_end, parent_id, metadata)`, `Query(id, text, expected_answer, gold_passages, answer_type, split)`, `RetrievedChunk(chunk, score, rank, source)`, `Context(text, chunks, chars, truncated)`, `Answer(text, raw_response, usage)`, `Usage(prompt_tokens, completion_tokens, calls)`, `StageTiming(stage, seconds)`
- [x] `core/contract.py`: `TechniqueSpec(name, version, family, description, params_schema, requires={embedder, llm, reranker, store…}, reference, status)`; `TechniqueDeps(retriever, embedder, llm, reranker, store, prompts, seed, logger)`; `TechniqueRequest(query, k, max_context_chars, params, filters)`; `TechniqueResult(answer, contexts, citations, diagnostics, timings, usage, warnings)`; protocolo `run(request, deps) -> TechniqueResult`
- [x] Validação do resultado: `core/contract.validate_result` verifica tipos, que `citations` apontem para chunks presentes em `contexts`, que `timings` cubra as etapas obrigatórias (`retrieval`, `generation`) e que `diagnostics` seja serializável
- [x] `core/registry.py`: descoberta automática de `ragstudio/techniques/*.py` e `*/technique.py` via `pkgutil`; `get(name)`, `list()` com spec e status; erro claro para nome inexistente; sem import de técnica pelo núcleo
- [x] `core/seeds.py` (seed global → `random`, `numpy`, parâmetro `seed` dos providers), `core/timing.py` (context manager que acumula `StageTiming`), `core/hashing.py` (JSON canônico + SHA-256, mesma regra do ledger do JudDoc_Ex), `core/logging.py` (logger estruturado para stderr), `core/errors.py` (`RagStudioError`, `ProviderError`, `ConfigError`, `ValidationError`)
- [x] CLI `techniques list` (spec, status, parâmetros, referência) e `techniques describe --name`
- [x] Testes: `test_models.py` (serialização ida e volta), `test_contract.py` (técnica de teste válida e inválida), `test_registry.py` (descoberta de um módulo fake em diretório temporário)
- [x] `docs/adding-a-technique.md`: passo a passo com o esqueleto mínimo de módulo (SPEC + run) e os testes esperados

## Fase 2 — Providers e adaptadores de modelos ✅
Sem provider mock não há teste; sem medição de tokens e custo não há dado comparável.

- [x] `providers/base.py`: `EmbeddingProvider.embed(texts) -> list[list[float]]` e `LLMProvider.chat(messages, temperature, max_tokens, seed) -> LLMResult(text, usage, raw, model, latency)`; toda chamada passa por um wrapper que mede latência e acumula `Usage`
- [x] `providers/mock.py`: embedding determinístico por bag-of-words hasheado (dimensão configurável) e LLM extrativo determinístico (portar `_mock_vector` e `_mock_chat` de `../JudDoc_Ex/Backend/rag/providers.py`); respostas a prompts de controle (multi-query, hypo doc, gap-query, confiança) também determinísticas
- [x] `providers/openai.py`, `providers/lmstudio.py`, `providers/ollama.py` sobre HTTP puro (`requests`), portando `_post`, `embed_batch`, `chat`, retry 429/5xx com backoff, tratamento de modelos de raciocínio (sem temperature/seed) e `list_models`
- [x] `providers/routing.py`: resolve endpoints a partir da config (LM Studio → Ollama → OpenAI, allowlist OpenAI), `test_connection`
- [x] `providers/pricing.json` + `providers/cost.py`: custo estimado por tokens; modelos sem preço registram `cost_usd = null` e aviso, nunca zero
- [x] `providers/fingerprint.py`: identificação de versão do modelo (id, `system_fingerprint` quando a API devolve, hash de resposta a prompt-sonda em provider local) gravada no snapshot de ambiente
- [x] Cache opcional de embeddings por `(provider, model, sha256(text))` em `Dados/indices/_embedding_cache.sqlite` para não pagar duas vezes pelo mesmo chunk
- [x] CLI `config show|set|test-connection|list-models`
- [x] Testes: `test_providers_mock.py` (determinismo), `test_providers_routing.py` (precedência local/OpenAI, erro "API key não configurada" sem servidor local), `test_cost.py`

## Fase 3 — Ingestão, perfil do corpus e chunking ✅
As características dos documentos são uma variável independente do experimento e precisam ser medidas na entrada.

- [x] `ingest/loaders/`: `markdown.py`, `text.py`, `pdf_docling.py` (import lazy; portar `ragkit/ingest_docling.py`), `json_corpus.py` (lista de documentos já em texto); detecção por extensão e validação (vazio, encoding, tamanho máximo)
- [x] `ingest/cleaner.py`: portar as flags de limpeza de Markdown do JudDoc_Ex (`remove_image_tags`, `remove_repeated_headers`, `collapse_blank_lines`, `remove_print_metadata`) com registro de qual limpeza foi aplicada
- [x] `ingest/profile.py`: perfil do corpus e de cada documento (número de documentos, chars, palavras, páginas, tipo de arquivo, idioma por heurística de stopwords pt/en, razão tabelas/listas, densidade de números, comprimento médio de parágrafo) gravado em `documents` e `corpora`
- [x] `ingest/splits.py`: `corpus_splits` (train/validation/test) por lista de `document_id` com hash, estratificação opcional por metadado; validação anti-vazamento usada pelo executor
- [x] `processing/chunking/`: `fixed.py` (chars + overlap, portar `ragkit/chunking.py` e `rag/chunking.py` do JudDoc_Ex), `markdown_headers.py` (por seção com herança de títulos), `sentence.py`, `parent_child.py` (chunk filho com `parent_id`); todas devolvem `Chunk` com offsets globais verificáveis (`document.text[start:end] == chunk.text`)
- [x] Perfil de chunking gravado por índice: quantidade, tamanho médio/mínimo/máximo, desvio, chunks truncados
- [x] CLI `corpus import --path --name [--format]`, `corpus list|describe|profile`, `corpus split --name --train/--validation/--test`
- [x] Testes: `test_loaders.py`, `test_cleaner.py`, `test_profile.py`, `test_chunking.py` (invariante de offsets para todas as estratégias), `test_splits.py` (vazamento detectado)

## Fase 4 — Índices e recuperação ✅
Índices compartilhados entre técnicas são o que torna a comparação justa e barata.

- [x] `stores/base.py`: `IndexStore.add(chunks, embeddings)`, `dense_search(query_vec, k, filters)`, `lexical_search(query, k, filters)`, `get(chunk_ids)`, `all_embeddings()`, `persist(path)`, `load(path)`; metadados do índice (`corpus_id`, `chunking`, `embedding_model`, `dim`, `created_at`, `index_hash`)
- [x] `stores/memory.py`: numpy + BM25 (`rank-bm25`, fallback por interseção de termos), persistido em `Dados/indices/<index_hash>/{chunks.jsonl, embeddings.npy, meta.json}`; filtros por metadado de documento (corrige o `filters` ignorado no `ragkit`)
- [x] `stores/duckdb.py`: porte de `ragkit/duckdb_schema.py` e `duckdb_store.py` (FTS + VSS/HNSW, fallback LIKE) atrás da mesma interface; dependência opcional
- [x] `stores/faiss.py` e `stores/chroma.py`: busca densa respondida pelo FAISS (`index.faiss`) ou pelo Chroma (`chroma/`), BM25 e arquivos do `MemoryStore`; dependências opcionais com erro que nomeia o `pip install`; opção `store` no runbook, na CLI e na interface
- [x] `retrieval/dense.py` (cosseno, checagem de dimensão com erro explícito), `retrieval/bm25.py`, `retrieval/hybrid.py` (soma ponderada normalizada, `dense_weight`), `retrieval/fusion.py` (RRF), `retrieval/mmr.py` (portar `ragkit/mmr.py` operando sobre candidatos do store); todas devolvem `RetrievedChunk` com `source` (`dense`/`bm25`/`hybrid`/`mmr`)
- [x] `rerankers/noop.py`, `rerankers/lexical.py` (JudDoc_Ex), `rerankers/llm.py` (portar `ragkit/rerankers.py` com parse robusto da lista), `rerankers/cross_encoder.py` (adaptador opcional sobre `sentence-transformers`, erro claro se ausente)
- [x] `experiments/index_builder.py`: constrói ou reutiliza índice por `index_hash`, grava embeddings com o cache da Fase 2, emite progresso `--stream`
- [x] CLI `index build --corpus --chunking --embedding-model [--store memory|duckdb|faiss|chroma]`, `index list|describe|delete`, `index search --query --mode dense|bm25|hybrid|rrf|mmr --k`
- [x] Testes: `test_store_memory.py` (persistência ida e volta, filtros), `test_store_duckdb.py` (pulado sem `duckdb`), `test_retrieval.py` (ordenação, dimensão divergente, RRF, MMR com `lambda_` 0 e 1), `test_rerankers.py`

## Fase 5 — Técnicas RAG, lote 1 (porte do `ragkit`) ✅
Converte os 7 algoritmos existentes ao contrato formal, cada um com teste offline e spec honesto.

- [x] `prompts/`: templates do `ragkit/prompts.py` versionados (`answer_from_context`, `multi_queries`, `hypo_doc`, `decompose`, `extract_essential`, `gap_query`, `rerank`, `confidence`) em pt e en, com `format_context` que registra truncamento; cada prompt usado em um run é deduplicado por hash no banco
- [x] `techniques/naive.py` (`rag_naive`; parâmetro `retrieval_mode` ∈ dense|bm25|hybrid|rrf cobre as variantes básicas de recuperação sem duplicar módulo)
- [x] `techniques/hyde.py` (`rag_hyde`; registra o documento hipotético em `diagnostics`)
- [x] `techniques/multi_query.py` (`rag_multi_query`; `n_queries`; registra as consultas geradas e a contribuição de cada uma ao pool)
- [x] `techniques/decomposition.py` (`rag_decomposition`; `n_subquestions`)
- [x] `techniques/iterative.py` (`rag_iterative`; `rounds`; registra o rastro de consultas por rodada)
- [x] `techniques/context_compression.py` (`rag_context_compression`; registra taxa de compressão por chunk)
- [x] `techniques/mmr_rag.py` (naive sobre `retrieval/mmr.py`; `lambda_`, `k_candidates`)
- [x] `techniques/rag_evo/` subpacote: `technique.py` (`rag_evo` v4), `heuristics.py` (`score_len`, `score_entropy`, `score_coverage`, `confidence_score`), `confidence.py` (modos `composite`, `heuristic`, `llm`); o log JSONL de rodadas passa a ser `diagnostics.traces` persistido pelo executor em vez de `logs/`
- [x] Toda técnica preenche `timings` por etapa (`query_transform`, `retrieval`, `rerank`, `compression`, `context`, `generation`) e `usage` agregado das chamadas de LLM, via `TechniqueDeps` instrumentado
- [x] Atualizar o catálogo deste roadmap e o `SPEC.status` de cada módulo (`implementado` só com teste passando)
- [x] Testes: um `tests/techniques/test_<nome>.py` por técnica rodando sobre `small_corpus` + mock e validando o resultado pelo `validate_result`; `test_all_techniques_contract.py` parametrizado sobre `registry.list()` garante que toda técnica registrada passa pelo mesmo fluxo
- [x] Arquivar `ragkit/` em `docs/legacy/ragkit/` (ou remover) depois que os testes de porte passarem, mantendo a atribuição de origem nos docstrings

## Fase 6 — Execução de experimentos e persistência ✅
Transforma técnicas em dados: grade de configurações, runs, resultados e evidências gravados de forma imutável.

- [x] `db/connection.py` (WAL, FK, busy_timeout, transação), `db/migrate.py` (migrações numeradas, idempotente), `db/backup.py`
- [x] `db/migrations/0001_initial.sql`: `corpora`, `documents`, `corpus_splits`, `indices`, `question_sets`, `questions` (versionadas, `supersedes_id`), `gold_passages`, `runbooks` (grade em JSON, status, orçamento), `runs` (técnica, versão, config JSON, `config_hash`, `index_hash`, status, timestamps), `query_results` (run, question, answer, contexto final, fontes, timings JSON, usage JSON, custo, warnings), `retrieved_chunks` (query_result, rank, chunk_id, score, source, text), `retrieval_metrics` e `generation_metrics` (uma linha por query_result, colunas tipadas), `run_metrics` (agregados por run), `evidence_events` (cadeia de hashes), `prompts` (dedup por SHA-256), `environment_snapshots`, `exports`, `run_logs`; triggers de imutabilidade em runs concluídos
- [x] `db/repository.py`: toda a SQL em um só lugar, funções tipadas por agregado; nenhuma SQL fora deste módulo
- [x] `experiments/runbook.py`: grade `técnicas × corpora/splits × índices (chunking × embedding) × LLMs × k × parâmetros da técnica × seeds`, estimativa de custo e tempo, validação anti-vazamento, presets `quick` / `comparative` / `full`
- [x] `experiments/runner.py`: executa cada run (monta `TechniqueDeps` a partir da config, chama `registry.get(name).run` por pergunta, grava resultado, eventos `request`/`response`/`retrieval`/`evaluation`/`error`/`retry`), retry com backoff, `cancel` por SIGTERM, `resume` pulando runs concluídos, progresso `--stream`, aviso e parada por orçamento
- [x] `experiments/artifacts.py`: JSONL por run em `Dados/runs/<run_id>/` (contexto completo, resposta bruta, diagnostics) com SHA-256 registrado em `exports`
- [x] Snapshot de ambiente por run (versões de pacotes, SO, commit git, provider, URL, modelo, fingerprint, seed); `config_hash` canônico; replay `experiments reproduce --run-id [--dry-run]` que cria réplica ligada por `replicates_run_id`
- [x] CLI `questions import-json|create|list|export`, `experiments preview|create|run --stream|list|status|show|reproduce|verify|delete-preview|delete --confirm|presets` (retomada é automática ao rodar de novo; cancelamento é por `Ctrl+C` / `SIGTERM`, sem comando próprio)
- [x] `configs/examples/`: `quick_mock.yaml` (roda offline em segundos), `compare_techniques.yaml`, `chunking_sweep.yaml`, `structure_techniques.yaml`, `provider_lmstudio.ini`
- [x] Testes: `test_db_migrations.py`, `test_repository.py`, `test_runbook.py` (tamanho da grade, custo, vazamento rejeitado), `test_runner_e2e.py` (runbook com 3 técnicas × 2 perguntas sobre mock: resultados gravados, cadeia de evidências verificável, resume não repete runs), `test_immutability.py` (UPDATE em run concluído é rejeitado)

## Fase 7 — Avaliação ✅
Separar o que pode ser medido automaticamente do que exige anotação, sem inventar número.

- [x] `evaluation/availability.py`: dado o question set e o run, lista métricas `available` e `requires_annotation` (gold passages → recuperação; resposta esperada → acurácia; nada → só latência/custo/tokens/cobertura de contexto)
- [x] `evaluation/retrieval_metrics.py`: `recall@k`, `precision@k`, `MRR`, `nDCG@k`, `hit@k` sobre gold passages (match por substring normalizada e por sobreposição de offsets quando o gold tem `char_start/char_end`); `context_coverage` (fração do gold presente no contexto final)
- [x] `evaluation/generation_metrics.py`: `exact_match`, `F1` de tokens, acurácia por tipo de resposta (boolean/extraction/classification), `faithfulness` e `groundedness` lexicais, `citation_accuracy`, `hallucination`, `refusal` (portar `Backend/experiments/evaluator.py` do JudDoc_Ex)
- [x] `evaluation/judge.py`: juiz LLM opcional com modelo configurável, prompt versionado, seed e temperatura 0; resultado gravado com o modelo juiz e o hash do prompt; no mock devolve valor determinístico marcado `judge=mock`
- [x] Métricas de eficiência por run: latência total e por etapa, tokens de entrada/saída, número de chamadas de LLM por pergunta (as técnicas iterativas fazem várias), custo estimado
- [x] `evaluation/aggregate.py`: agregados por run (média, mediana, desvio) gravados em `run_metrics`; quadrante acurácia × fidelidade
- [x] Reavaliação sem reexecutar: `evaluate rerun --run-id` recalcula métricas a partir dos artefatos gravados (nova linha versionada em `*_metrics`, nunca sobrescreve)
- [x] `evaluation/human_review.py` + tabela `answer_reviews` (verdict, note, reviewer) para concordância juiz × humano
- [x] CLI `evaluate availability --question-set`, `evaluate rerun --run-id`, `evaluate metrics`, `evaluate review-add`, `evaluate agreement` (a avaliação inicial acontece dentro do run)
- [x] Testes: `test_retrieval_metrics.py` (casos com gabarito manual), `test_generation_metrics.py`, `test_availability.py` (question set sem gold não produz métricas de recuperação), `test_evaluate_rerun.py`

## Fase 8 — Comparação e análise empírica ✅
É o objetivo final do RagStudio: dados comparáveis por técnica, corpus e características dos documentos.

- [x] `analysis/compare.py`: tabela longa (uma linha por run × pergunta × métrica) e larga (técnica × métrica) por runbook; comparação pareada de dois runs com diff de configuração e deltas
- [x] `analysis/stats.py`: testes pareados por pergunta (Wilcoxon, t pareado, bootstrap de intervalo de confiança), correção para múltiplas comparações, tamanho de efeito; réplicas por seed agregadas
- [x] `analysis/characteristics.py`: cruzamento das métricas com o perfil do corpus e dos documentos (tamanho, número de chunks, idioma, tipo de arquivo, densidade de tabelas) por correlação e por faixas; saída pronta para gráfico
- [x] `analysis/exports.py`: CSV, Parquet e JSON em `Dados/exports/` com SHA-256 registrado; `exports schema` documenta as colunas
- [x] `reports/charts.py` (matplotlib, paleta única, rótulos em inglês, PNG 300 dpi + SVG + PDF; figura sem dados levanta `SkipFigure`): barras por técnica e métrica, latência por etapa empilhada, custo × acurácia, recall@k por k, métrica × característica do documento
- [x] `reports/tables.py` (LaTeX, CSV, Markdown) e `reports/html_report.py` (Jinja2, autocontido) com seção *Experimental Setup* gerada do snapshot de ambiente
- [x] CLI `compare runs --ids`, `compare runbook --id [--by technique|corpus|chunking]`, `compare characteristics --runbook-id`, `reports html|figures|tables|export --format`
- [x] Testes: `test_compare.py`, `test_stats.py` (dados sintéticos com efeito conhecido), `test_reports.py` (HTML gerado a partir do runbook e2e do mock)

## Fase 9 — Técnicas RAG, lote 2 e lote 3 ✅
Amplia o catálogo primeiro com técnicas sem infraestrutura nova, depois com as que exigem adaptadores.

Lote 2 (sem infraestrutura nova):
- [x] `techniques/step_back.py` (pergunta abstrata + pergunta original, pool unido)
- [x] `techniques/parent_child.py` (usa `processing/chunking/parent_child.py`; recupera filhos, contexto com pais deduplicados)
- [x] `techniques/sentence_window.py` (recupera sentença, expande janela ±n no documento original)
- [x] `techniques/contextual_retrieval.py` (prefixo por chunk gerado por LLM na indexação; exige `index_builder` com etapa de enriquecimento registrada no `index_hash`)
- [x] `techniques/corrective.py` (CRAG-like: avalia relevância dos chunks, descarta e reconsulta; registra decisões)
- [x] Fusão como opção transversal: `retrieval_mode=rrf` disponível em todas as técnicas de consulta

Lote 3 (exigem adaptadores ou índices próprios; entram como `protótipo`/`adaptador` até terem teste completo):
- [x] `techniques/raptor/` (árvore de resumos por clustering; índice próprio persistido junto ao `index_hash`)
- [x] `stores/graph.py` (adaptador de grafo em memória com `networkx` opcional) + `techniques/graph_rag/` (extração de entidades/relações por LLM na indexação, recuperação por vizinhança)
- [x] `techniques/agentic/` (loop de decisão com ferramentas `search`, `read_document`, `answer`; limite de passos; rastro completo em `diagnostics`)
- [x] Para cada nova técnica: módulo + `SPEC` + teste com mock + linha no catálogo + nota em `docs/techniques.md` com a referência acadêmica (estender ` Técnicas de RAG Implementadas no Projeto.md`)

## Fase 10 — Documentação, exemplos e qualidade 🟡
Critério de aceitação: outra pessoa adiciona uma técnica sem tocar no núcleo e reproduz um experimento só com o README.

- [x] `README.md`: propósito, instalação, fluxo completo em CLI (import → index → questions → experiments → evaluate → compare → reports) com o exemplo `quick_mock.yaml`, como ligar um provider real
- [x] `docs/running-experiments.md`, `docs/comparing.md`, `docs/adding-a-technique.md` (atualizado com um exemplo real do lote 2), `docs/data-schema.md` (tabelas, colunas exportadas, formato dos artefatos), `docs/techniques.md` (catálogo com status e referências)
- [x] `CLAUDE.md` completo (comandos, arquitetura, contrato, regras de dados, pitfalls encontrados)
- [x] `scripts/check.sh` limpo (ruff + pytest offline) e workflow de CI em `.github/workflows/ci.yml`
- [ ] Teste de integração com provider real: `tests/test_integration_real.py` está escrito e é pulado por padrão; **falta executá-lo** com um modelo local ou API (`RAGSTUDIO_INTEGRATION=1`, ver docstring do arquivo)
- [x] Validação dos critérios de aceitação do prompt principal, item a item, registrada no fim deste roadmap
- [x] `DCR/` com lições aprendidas (contrato de técnica, índice compartilhado por hash, avaliação sem gold) usando a skill `DCR-licoes`

## Fase 11 — Interface desktop 🟡
Construída em 2026-10-12 a pedido do usuário, reaproveitando a casca do JudDoc_Ex (ponte Electron → Python, layout, shadcn/ui).

- [x] Decisão: construir. A primeira decisão registrada ("não construída") foi revista quando o usuário pediu a interface como no JudDoc_Ex
- [x] `Frontend/`: Electron + Vite + React 19 + TypeScript + Tailwind 4 + shadcn/ui; `src/main/python.ts` (spawn de `python -m ragstudio`, streaming, cancelamento), `ipc.ts`, `preload`, protocolo `ragstudio://` para figuras
- [x] `lib/api.ts` (cliente tipado da CLI) e `lib/types.ts` (formas do JSON do backend)
- [x] Comandos de backend criados para a interface, com teste: `config set-many`, `corpus document`, `questions archive`, `experiments answer`, `experiments evidence`, `compare table`, `compare answers`
- [x] Tela **Corpus**: importação, tabela de documentos com perfil, visualização do texto, características, splits, índices (construção com progresso e teste de recuperação)
- [x] Tela **Perguntas**: conjuntos, importação de JSON com ancoragem, criação e edição com trechos gold, arquivamento, exportação, métricas disponíveis
- [x] Tela **Técnicas**: catálogo com filtro por status
- [x] Tela **Experimentos**: Montar (três colunas numeradas e barra de revisão fixa, cabe em 1280×800), Monitor com streaming, Resultados (tabela ordenável, detalhe do run, respostas, evidências, reavaliar, reproduzir), Comparar (run × run com estatística pareada)
- [x] Comparador visual de técnicas por pergunta: resposta de cada run lado a lado, com métricas, e painel de detalhe com chunks, trechos gold, tempo por etapa e revisão humana
- [x] Tela **Análise**: métricas por eixo de configuração e correlações com as características dos documentos
- [x] Tela **Relatórios**: relatório HTML, figuras com prévia, tabelas e exportações registradas
- [x] Tela **Configurações**: provider e modelos com teste de conexão, padrões de experimento, aparência, banco
- [x] i18n pt-BR / en por página (chaves conferidas pelo TypeScript) e tema claro / escuro
- [x] `run.sh` na raiz com 7 verificações e abertura do app (`--dev`, `--demo`, `--no-app`); `scripts/check.sh` e CI incluem o Frontend
- [x] Verificação por screenshot do app rodando (CDP) em 1440×900 e 1280×800, tema claro e escuro, pt-BR e en; runbook criado e executado pela própria interface
- [x] Telas revistas depois do primeiro uso real: Comparar › Por pergunta virou tabela com filtros por eixo, agrupamento por técnica ou por resposta igual, paginação e até 4 respostas lado a lado (antes eram 960 colunas horizontais); aba Splits com proporções esperadas, participação em documentos e caracteres, busca e listas roláveis (antes as linhas se sobrepunham)
- [x] Montar: rerankers e stores sem o pacote instalado aparecem desabilitados com o `pip install` necessário (`experiments options`)
- [x] Tela **Referências** (grupo Apoio do menu): 105 verbetes em pt-BR e en sobre técnicas, componentes, métricas, estatística e conceitos, 9 guias de execução e leitura de resultados, e bibliografia com 41 fontes. Busca sem acento, abas por tipo, links cruzados e endereço por verbete (`#/references?id=metric.recall`). Conteúdo em `ragstudio/reference/` e na CLI (`reference list|show`); as técnicas vêm do registry, e `tests/test_reference.py` falha se uma técnica, métrica ou opção de runbook ficar sem verbete
- [ ] Ligar as outras telas às Referências (por exemplo, o cabeçalho de cada métrica abrir o seu verbete)
- [ ] Exercitar com provider real, e conferir à mão o que a automação não cobre: seletor de arquivos nativo, cancelamento de um run longo, exclusão de runbook
- [ ] Empacotamento com `electron-builder` (`npm run build:mac`): configuração herdada, nunca executada
- [ ] Testes automatizados do Frontend (hoje só typecheck, lint e build)

---

## Fase 12 — Catálogo ampliado e nomes de exibição ✅
Pedido do usuário em 2026-10-12: implementar as abordagens que faltavam de uma lista de 14, completar os três protótipos e mostrar nomes legíveis.

- [x] `TechniqueSpec.title`: nome de exibição ("Corrective RAG") separado do identificador estável (`corrective`), que continua no runbook e nos runs gravados. Telas, figuras e tabelas de relatório usam o nome; exportações mantêm o identificador
- [x] Grafo de conhecimento compartilhado: `stores/graph.py` (`KnowledgeGraph` com entidades e relações tipadas, `louvain`) e `techniques/_kg.py`. Uma única extração por índice serve a GraphRAG, LightRAG e HippoRAG
- [x] `graph_rag` 1.0: relações tipadas, comunidades hierárquicas, relatórios de comunidade, busca local e busca global por map-reduce
- [x] `raptor` 1.0: árvore recursiva, redução (UMAP opcional, PCA), mistura gaussiana suave com BIC, modos `collapsed` e `tree_traversal`
- [x] `agentic` 1.0: planejamento, ferramentas `search`, `keyword_search`, `read_more` e `finish` por tool calling nativo, com recuo para protocolo de texto
- [x] Tool calling nativo no núcleo: `Tool` / `ToolCall`, `deps.ask_tool`, `routing.chat(tools=...)`, cliente OpenAI-compatível e mock; testado contra o servidor HTTP falso
- [x] `deps.log_retrieval`: evidência para rankings calculados pela própria técnica (grafo, árvore)
- [x] Novas: `light_rag`, `hippo_rag`, `adaptive_rag`, `multi_hop`, `hybrid_rag`, `rag_fusion`, e os protótipos `self_rag` e `rank_rag`
- [x] Técnicas que respondem sem recuperar (`adaptive_rag` rota A, `self_rag`): contexto vazio aceito pelo executor e pela avaliação
- [x] Testes: contrato para as 24 técnicas, comportamento de cada nova, runbook com o catálogo inteiro, verbetes na tela Referências
- [ ] Rodar as 11 técnicas novas ou reescritas com um provider real e conferir prompts e análise das respostas (formato `ENTITY | ...`, `SUPPORT:`, `HIGH:` / `LOW:`)
- [ ] Medir o custo de construção do grafo e da árvore em um corpus real antes de incluí-los em uma grade grande
- [ ] Instalar e exercitar `umap-learn` no RAPTOR
- [ ] Self-RAG e RankRAG com os modelos treinados dos artigos (hoje são aproximações por prompt)

---

## Fase 13 — Etapas do pipeline, poda da grade e itens que cabem no desenho ✅
Pedido do usuário em 2026-10-12, depois da avaliação de três listas de arquiteturas, algoritmos e técnicas de processamento.

- [x] `SPEC.stage`: etapa do pipeline em que a técnica atua (documento e índice, consulta, recuperação, pós-recuperação, orquestração). Montar, Técnicas e Referências agrupam por etapa
- [x] `SPEC.ignores`: configurações do run que a técnica substitui (modo de recuperação, reranker, contexto máximo), fixas ou em função dos parâmetros
- [x] Poda no runbook (`prune`, padrão ligado): combinações redundantes e incompatíveis não viram runs; `preview` e `create` devolvem o resumo; eixos ignorados aparecem como `n/a` nas tabelas
- [x] Chunking `recursive` e `semantic` (este com embedder na indexação e custo registrado no índice)
- [x] Técnicas `long_context`, `hierarchical`, e os protótipos `recomp` e `speculative_rag`
- [x] Verbetes de Referências para as técnicas e chunkings novos, para as etapas do pipeline e para a poda
- [ ] Rodar com provider real as 4 técnicas e os 2 chunkings novos
- [ ] Decidir sobre os itens que ficaram de fora por dependerem de modelos locais ou por pouco retorno neste corpus: SPLADE, ColBERT, late chunking, chunking por proposições, TF-IDF, IVF e PQ
- [ ] Fora de escopo, registrado para não voltar à discussão: Fusion-in-Decoder (exige modelo leitor treinado), ScaNN e DiskANN (escala de milhões de vetores), Multimodal RAG e VisRAG (outro pipeline, com imagens)

---

## Ordem recomendada

1. **Fase 0 → 1 → 2** são sequenciais e bloqueiam tudo: sem contrato e sem mock não há como testar uma técnica.
2. **Fase 3 e Fase 4** podem andar em paralelo depois da Fase 1 (ingestão não depende de store; store não depende de loaders), mas a Fase 4 precisa dos `Chunk` da Fase 3 para o teste de ponta a ponta.
3. **Fase 5** depende de 2, 3 e 4. Portar primeiro `naive` (valida todo o fluxo), depois `hyde`, `multi_query`, `decomposition`, `iterative`, `context_compression`, `mmr_rag` e por último `rag_evo` (o mais complexo).
4. **Fase 6** pode começar a camada `db/` logo após a Fase 1 (o schema só depende dos modelos), em paralelo com 3–5; o `runner` só fecha depois da Fase 5.
5. **Fase 7** depende de 6. **Fase 8** depende de 7.
6. **Fase 9** depende de 5 e 6 e pode ser intercalada com 7 e 8: cada técnica nova é independente das outras.
7. **Fase 10** acompanha todas as fases (documentar ao concluir cada uma) e fecha no fim. **Fase 11** (interface) depende só da CLI estar estável.

**Primeiro marco verificável:** fim da Fase 6 com o runbook `quick_mock.yaml` rodando 3 técnicas × 2 perguntas offline e gravando resultados comparáveis no SQLite.

---

## Critérios de aceitação (do prompt principal)

Conferidos em 2026-10-12. Todos valem com o provider mock; nenhum foi conferido com LLM real.

- [x] 1. Nova técnica adicionada sem alterar o núcleo. Evidência: `test_registry_discovers_external_technique_without_touching_core` carrega uma técnica de uma pasta externa e a executa; as 8 técnicas do lote 2 e 3 entraram só com arquivos novos em `techniques/`, templates de prompt e regras do mock
- [x] 2. Técnicas diferentes executadas pelo mesmo executor e contrato. Evidência: `tests/techniques/test_all_techniques.py` (28 técnicas × 3 configurações) e `test_end_to_end_three_techniques`
- [x] 3. Resultados comparáveis por experimento, corpus e técnica. Evidência: `compare runbook --by`, `compare runs`, tabelas `runs` / `questions` / `characteristics`
- [x] 4. Configurações e parâmetros preservados por run. Evidência: `config_hash`, `index_hash`, `environment_snapshots`, `prompts` por hash, `experiments reproduce` com 100 % de respostas idênticas no mock
- [x] 5. Fluxo documento → processamento → resultado representado no código (`ingest` → `processing` → `stores` / `retrieval` → `techniques` → `experiments` → `evaluation` → `analysis`)
- [x] 6. Técnicas com dependências específicas isoladas por adaptadores ou subpacotes (`rag_evo/`, `raptor/`, `graph_rag/`, `agentic/`, `stores/duckdb.py`, `stores/graph.py`, `rerankers/cross_encoder.py`)
- [x] 7. Testes para contratos e componentes principais (346 testes)
- [x] 8. Sistema funciona com mock, sem serviço pago
- [x] 9. Documentação explica como executar, comparar e adicionar técnicas (`docs/running-experiments.md`, `docs/comparing.md`, `docs/adding-a-technique.md`)
- [x] 10. Limitações e funcionalidades não implementadas explícitas (`SPEC.status`, `warnings` por resposta, `docs/techniques.md`, seção "Estado atual")

---

## Próximos passos sugeridos

1. Ligar um provider real (LM Studio, Ollama ou OpenAI) e rodar `tests/test_integration_real.py`, depois `configs/examples/compare_techniques.yaml` sobre um corpus de interesse.
2. Conferir se os modelos respeitam os formatos pedidos pelos prompts de controle (listas sem numeração, "sim/não", nota de 0 a 1) e ajustar `prompts/templates.py`.
3. Montar um question set com gold passages e respostas esperadas no corpus real: sem isso só há métricas de eficiência e de fidelidade lexical.
4. Instalar Docling e validar o loader de PDF em documentos reais.
5. Comparar as heurísticas lexicais de geração com o juiz LLM e com revisão humana antes de usá-las em artigo.
6. Completar os protótipos conforme a necessidade (RAPTOR recursivo, GraphRAG com comunidades, agente com tool calling).
7. Exercitar a aplicação desktop com provider real e decidir sobre o empacotamento (Fase 11).
