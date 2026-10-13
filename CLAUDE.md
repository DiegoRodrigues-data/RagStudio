# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**RagStudio** is a desktop application (Electron + React 19 + shadcn/ui frontend, Python 3.11 backend, SQLite) to
implement, run, compare and validate RAG techniques reproducibly. Every technique obeys one contract and one flow
(document → chunking → index → retrieval → context → generation → evaluation); the product is comparable data per
technique, corpus and document characteristics. The backend is also a complete CLI on its own.

`ROADMAP.md` tracks phase status (keep its checkboxes in sync when finishing work). `docs/` holds the user guides in
Portuguese. `docs/legacy/ragkit/` is the archived source of the first seven algorithms: never import or edit it.
The structural reference is the sibling project `../JudDoc_Ex` (CLI JSON contract, SQLite ledger, mock provider).

## Commands

```bash
./run.sh                           # 7 checks (conda → Python deps → DB migrate → provider → Node → npm deps → Electron) then the app
./run.sh --dev | --demo | --no-app # HMR · offline demo with the mock provider · checks only (CLI use)
./rs <group> <command> [flags]     # CLI launcher; resolves the conda env `ragstudio` (or $RAGSTUDIO_PYTHON)
scripts/check.sh [--backend]       # ruff + pytest + frontend typecheck/lint/build: everything CI runs

# Frontend (from Frontend/)
npm run check                      # typecheck (node + web) + eslint
npm run build                      # electron-vite build
npm run dev -- --remoteDebuggingPort 9222   # app with HMR, drivable over CDP for screenshots

/opt/miniconda3/envs/ragstudio/bin/python -m pytest tests -q                           # offline, deterministic
/opt/miniconda3/envs/ragstudio/bin/python -m pytest tests/test_db.py -q                # one file
/opt/miniconda3/envs/ragstudio/bin/python -m pytest tests/techniques -q -k rag_evo     # by keyword
/opt/miniconda3/envs/ragstudio/bin/python -m pytest "tests/test_runbook_runner.py::test_budget_is_enforced" -q   # one test
/opt/miniconda3/envs/ragstudio/bin/python -m ruff check ragstudio tests
```

The Python environment is the conda env `ragstudio` (`environment.yml`; `requirements.txt` is the pip fallback).
The Frontend has no test runner: `npm run check` and `npm run build` are its whole automated verification.

Groups: `db config corpus index techniques questions experiments evaluate compare reports reference`. Every command
prints exactly one final JSON line, `{"ok":true,"data":…}` or `{"ok":false,"error":…,"error_type":…}`; `--stream` commands
print `{"progress":…}` lines before it; logs go to stderr; exit codes 0 / 1 (handled error) / 2 (usage).

To exercise anything without touching real data or spending tokens: `RAGSTUDIO_PROVIDER=mock` plus a scratch
`RAGSTUDIO_DATA_DIR` (and `RAGSTUDIO_DB`, `RAGSTUDIO_CONFIG`). Demo data: `tests/fixtures/docs` (3 Markdown
documents in pt-BR) and `tests/fixtures/questions.json`.

**`Dados/` holds the user's real experiments (paid OpenAI runs). Never run, migrate or modify it to test
something, and never re-run a real runbook on the user's behalf.** To look at the app at realistic scale, copy
the database (`sqlite3 Dados/ragstudio.sqlite ".backup <scratch>/copy.sqlite"`) and point `RAGSTUDIO_DB` at the copy.

## Architecture

```
ragstudio/cli.py            argparse groups → cli_groups/<group>_cmd.py; handlers return data, main() wraps the contract
ragstudio/core/             models (frozen dataclasses) · contract (TechniqueSpec/Request/Deps/Result, validate_result)
                            registry (discovery) · pipeline (shared building blocks) · hashing · seeds · timing · paths
ragstudio/providers/        Endpoint + routing.chat()/embed() · mock (rule per prompt task) · openai_compat (plain HTTP)
                            cost + pricing.json · cache (embeddings) · fingerprint
ragstudio/ingest/           loaders/ · cleaner · profile (document characteristics) · splits (leakage) · questions
ragstudio/processing/       chunking/ (fixed, recursive, sentence, semantic, markdown_headers, parent_child) · normalize
ragstudio/stores/           base (IndexStore protocol, IndexMeta) · memory (numpy + BM25) · duckdb · faiss · chroma · graph
ragstudio/retrieval/        dense · bm25 · hybrid · fusion (RRF) · mmr · retrieve() dispatcher
ragstudio/rerankers/        lexical · llm · cross_encoder · build()
ragstudio/prompts/          templates.py (pt/en, PROMPT_SET_VERSION) · PromptSet.render() with template hash
ragstudio/techniques/       one module (or package with technique.py) per technique: SPEC + run()
                            _kg (shared knowledge graph) · _multihop · _vectors: helpers the registry skips
ragstudio/experiments/      runbook (grid, leakage check, estimate) · runner · deps (instrumentation) · index_builder
                            artifacts (JSONL) · environment (snapshot)
ragstudio/evaluation/       retrieval_metrics · generation_metrics · judge · availability · aggregate · service
ragstudio/analysis/         compare · stats (paired tests) · characteristics · exports
ragstudio/reference/        catalog(language): entry (pt/en text) · metrics · techniques (prose; facts from the registry)
                            components · concepts (+ statistics) · guides · sources (bibliography)
ragstudio/reports/          style · charts (matplotlib) · tables · html_report (+ template.html)
ragstudio/db/               connection · migrate (migrations/NNNN_*.sql) · repository.Repo (ALL SQL) · backup
Frontend/src/main/          Electron main: python.ts (interpreter resolution, spawn `python -m ragstudio`, streaming) · ipc.ts · ragstudio:// protocol
Frontend/src/preload/       contextBridge → window.api {run, stream, cancelStream, onProgress, dialogs, shell, getPaths}
Frontend/src/renderer/src/  lib/api.ts (typed CLI client) · lib/types.ts (JSON shapes) · pages/<page>/ · components/shared · components/ui (shadcn)
```

### Renderer → main → Python
- `window.api.run(argv)` spawns `python -m ragstudio …argv` with `cwd = project root`; the last stdout line is the
  result. `window.api.stream(id, argv)` forwards each `{"progress": …}` line as `python:progress {id, event}` and
  delivers the final contract line as `{id, done, code, result}`; `cancelStream` sends SIGTERM (the runner marks the
  run `cancelled`).
- `lib/api.ts` builds argv from objects: camelCase keys become `--kebab-case`, arrays/objects become one JSON string,
  `true` is a bare flag, `false`/`undefined`/`''` are omitted, `stream()` appends `--stream`.
- Electron never opens the database. Each call is a fresh Python process (~230 ms measured for `db status`), so
  avoid chatty call patterns in the UI.
- Generated files (figures) reach the renderer through `ragstudio://local/<path>`, restricted to the project root,
  `RAGSTUDIO_DATA_DIR`, temp and userData; the CSP allows `img-src ragstudio:`.
- Commands that exist mainly for the UI: `config set-many`, `corpus document`, `questions archive`,
  `experiments answer|evidence|options`, `compare table|answers`, `reference list` (covered by
  `test_commands_used_by_the_desktop_app`).

### Technique contract
- A technique never opens connections, reads config, picks a model or calls a provider. It only uses `deps`:
  `ask(task, **vars)`, `ask_tool(task, tools, **vars)` (native tool calling, returns a `ToolCall`), `embed`,
  `retrieve`, `rerank`, `stage(name)`, `store`, and `log_retrieval(query, mode, items)` for a ranking it computed
  itself (graph, tree), so that ranking is in the evidence chain too. That is what keeps timing, token
  accounting and evidence identical across techniques (`experiments/deps.py`).
- The core never imports a technique by name. `core/registry.py` discovers `ragstudio/techniques/*` and the
  directories in `RAGSTUDIO_TECHNIQUES_PATH`; names starting with `_` are skipped.
- `validate_result` is applied to every result by the runner: citations and context chunk ids must be in
  `contexts`, timings must cover `retrieval` and `generation`, `diagnostics["technique"]` must equal the spec name.
- `SPEC.name` is the stable identifier stored with every run and used in runbooks; never rename it. `SPEC.title` is
  the display name ("Corrective RAG") shown by the UI (`useTechniqueTitle`, `<TechniqueName>`), figures and report
  tables (`registry.with_titles`); data exports keep the identifier.
- GraphRAG, LightRAG and HippoRAG read ONE extracted graph per index (`techniques/_kg.py`, task `kg_extract`,
  one LLM call per chunk). Keep `_kg.KG_PARAMS` in the SPEC of any new graph technique so it shares the cache.
- A result may have no contexts (`pipeline.answer_without_retrieval`: Adaptive RAG route A, Self-RAG); synthetic
  passages (summaries, community reports) are `pipeline.synthetic_chunk` with `index = -1`.
- `SPEC.stage` says where the technique acts (`PIPELINE_STAGES`); the UI groups by it. `SPEC.ignores` lists the run
  settings the technique replaces with its own (`retrieval_mode`, `reranker`, `max_context_chars`), as a tuple or a
  function of the resolved params. Keep it true to the code: `runbook.expand_with_report` prunes on it (a technique
  that never calls `select()` ignores the reranker; one that forces `mode=` ignores the retrieval mode), and
  `compare.config_columns` shows an ignored axis as `n/a`. `index:parent_child` / `index:contextual` in
  `SPEC.requires` prune the combinations that do not build that index.
- `SPEC.status` must be honest: `implemented` only with passing tests; reduced-scope work is `prototype` and says
  what is missing in its docstring and in `warnings`.
- A new prompt task needs both languages in `prompts/templates.py` and a rule in `providers/mock.py` `_RULES`,
  nothing else. `deps.ask` passes `task` and the variables to the mock, which never parses prompt text. Prefer
  reusing a task (`answer`, `summarize`, `relevance`, `confidence`, `entities`, `multi_queries`) over a new one.
- Adding a technique, end to end: the module with `SPEC` (`name`, `title`, `stage`, `ignores`, `status`) and `run`;
  its name in `EXPECTED` (and the prototype set) of `tests/techniques/test_all_techniques.py`; a behaviour test in
  `tests/techniques/test_specific.py`; prose in both languages in `reference/techniques.py` with sources in
  `reference/sources.py`; a row in `docs/techniques.md`. `docs/adding-a-technique.md` is the user-facing version.
- Validation state: only the 16 techniques of the first version ran against a real LLM (the user's run of
  2026-10-12). The 12 added later and the rewritten `graph_rag`, `raptor` and `agentic` ran with the mock only, so
  their prompt formats (`ENTITY | …`, `SUPPORT:`, `HIGH:` / `LOW:`, tool calls) are unproven on real models.

### Data rules
- **Python is the only writer of SQLite and all SQL lives in `db/repository.py`.**
- **Index identity.** `index_hash` = documents (id + sha256) + chunking + embedding provider/model + store + split +
  enrichment. Same hash means shared vectors; runs record it. Indices are files under `Dados/indices/<hash>/`.
- **Chunk invariant.** `document.text[chunk.char_start:chunk.char_end] == chunk.text` for every strategy; gold
  passages, parent expansion and sentence windows rely on it. Enrichment changes the *index text*, never the chunk.
- **Immutability.** Triggers reject UPDATE/DELETE on `query_results`, `retrieved_chunks`, `evidence_events` of
  completed runs. Completed runs are always skipped; re-running is `experiments reproduce` (replica linked by
  `replicates_run_id`). Runs that did not complete are reset and restarted from scratch.
- **Evidence chain.** `Repo.add_evidence` stores canonical JSON with `chain = sha256(prev_chain + payload_sha)`;
  `verify_chain` re-canonicalizes before hashing.
- **Metrics are append-only** (`eval_version`). A metric that cannot be measured is `None`/NULL, never 0; an unknown
  model price gives `cost_usd = None`.
- **Leakage.** `runbook.resolve_data` enforces splits: declared split → only its documents and questions; a tagged
  question with gold outside its split raises `LeakageError`; tagged questions without a declared split also raise.
- Schema changes are new files in `db/migrations/`; never edit an applied one. A new metric needs a column there,
  `Repo.add_metrics`/`result_metrics`, and `MEAN_METRICS` in `evaluation/aggregate.py`.

### Tests
`tests/conftest.py` has an autouse `isolated_env` (temp data dir, DB and config; provider mock). Fixtures:
`documents`, `repo`, `populated` (corpus `energia` + question set), `store` (small index), `make_deps(**overrides)`.
`tests/techniques/test_all_techniques.py` is parametrized over the registry and runs every technique through the
same contract checks; `tests/test_reference.py` fails when a technique, metric or runbook option has no reference
entry. A mock rule that answers `{"tool": name, "arguments": {...}}` is delivered as a native tool call when tools
were offered. `tests/test_http_provider.py` drives the real HTTP client against a local fake OpenAI-compatible
server. `tests/test_integration_real.py` is opt-in (`RAGSTUDIO_INTEGRATION=1`) and spends real tokens.

## Conventions
- A new CLI command the UI uses needs three things: the handler in its `cli_groups/*_cmd.py`, a wrapper in
  `Frontend/src/renderer/src/lib/api.ts` with the response type in `lib/types.ts`, and a test in
  `tests/test_cli_contract.py`.
- UI strings live next to the page: `pages/<page>/i18n.ts` (`pt` object + `en: Record<Key, string>` so missing keys
  fail the typecheck), used through `usePageT(dict)`. Global `locales/*.json` hold only navigation, page titles,
  statuses, pipeline stages (`stage.*`), run axes (`axis.*`) and common words. Metric names stay in English
  everywhere (`components/shared/metrics.ts`). Technique names are shown through `useTechniqueTitle` /
  `<TechniqueName>`, never by printing the identifier.
- Data loading: `useApiData(loader)` with `useMemo(() => (id ? () => api.x(id) : null), [id])` so nothing is fetched
  without a selection. Stream completion is handled with `useStreamDone`, never by `setState` inside an effect
  (the lint rule `react-hooks/set-state-in-effect` is on).
- A file that exports a component exports only components (`react-refresh/only-export-components`); helpers go to
  `lib/` or a sibling `.ts`.
- The References page (`pages/references/`, menu group Support) renders `reference list --language pt|en`. Its
  content lives in `ragstudio/reference/`, not in the frontend. A new technique needs prose in
  `reference/techniques.py`; a new metric, retrieval mode, reranker, chunking strategy or store needs an entry;
  `tests/test_reference.py` fails otherwise. Entries describe what THIS code computes (thresholds, defaults), in
  both languages with the same sections. Keywords are never translated: metric, technique and option names,
  `chunk`, `embedding`, `runbook`, `run`, `seed`, `split`, `index_hash`, `top-k`. A source goes into
  `reference/sources.py` with `checked` set only after the link was actually resolved.
- A chunking strategy needs `processing/chunking/__init__.py` (`STRATEGIES`), the two UI lists
  (`pages/experiments/draft.ts`, `pages/corpus/indices-tab.tsx`), a case in `tests/test_chunking.py` and an entry
  in `reference/components.py`. One that needs embeddings goes in `NEEDS_EMBEDDER`; the index builder passes the
  embedder and records the cost in `build_usage.chunking_embedding_tokens`.
- Store adapters subclass `MemoryStore` and replace only the search engine (`faiss`: exact `IndexFlatIP`; `chroma`:
  approximate HNSW). A new one needs `stores/__init__.py` (`KINDS`, `create`, `load`), the two UI lists
  (`pages/experiments/draft.ts` `STORES`, `pages/settings/index.tsx`) and a case in `tests/test_stores_retrieval.py`.
  Chroma keeps one live client per directory in the process: `stores/chroma.py` closes it before a rebuild.
- Numbers produced by the mock provider are always labelled (`MockBadge`) wherever results are shown.
- Product rules from the user: screens use the horizontal space (Experiments › Setup is three numbered columns plus
  a sticky review bar and fits 1280×800), side sheets are wide enough to read, `run.sh` lives at the project root,
  and layout changes are verified with a real screenshot of the running app, not by build alone.
- English identifiers, docstrings, report labels and chart text. Portuguese in `README.md`, `ROADMAP.md`, `docs/`
  and in the `pt` prompt templates.
- Functions with type hints, frozen dataclasses for records; classes only where state is needed (`Repo`, stores,
  `Runner`, `Judge`).
- Paths are resolved at call time through `core/paths.py`. Never copy a path into a module-level constant, or tests
  escape isolation.
- `docling` is in `environment.yml` (PDF import) but stays lazily imported, with one converter per process
  (`ingest/loaders/pdf_docling.py`); `corpus import --stream` reports per-file progress because conversion is slow.
- Optional heavy dependencies (`duckdb`, `faiss-cpu`, `chromadb`, `docling`, `sentence-transformers`, `pyarrow`,
  `umap-learn`) are imported inside the function that needs them, with a `ValidationError` naming the
  `pip install`. `umap-learn` is not installed: RAPTOR falls back to PCA and records which reduction it used.
- Charts follow `reports/style.py` (validated categorical order, single hue for one series, no dual axes, PNG 300 dpi
  + SVG + PDF); a figure without data raises `SkipFigure`.

## Pitfalls
- `Frontend/node_modules` is synced through Dropbox, so the Electron binary can be missing, corrupted or the wrong
  architecture. `run.sh` step 7 detects and reinstalls it; `Frontend/scripts/ensure-electron.cjs` runs on postinstall.
  Keep `overrides.extract-zip.yauzl >= 3` in `package.json`.
- shadcn components rely on React 19 (ref-as-prop); do not downgrade React. `components/ui/sheet.tsx` was edited so
  callers can set the width with `sm:max-w-*`; re-apply if regenerated.
- The app shell scrolls inside `<main>` (`components/app-layout.tsx`), not the window: sticky bars depend on it.
- To verify UI work: start `npm run dev -- --remoteDebuggingPort 9222` with `RAGSTUDIO_PROVIDER=mock` and scratch
  `RAGSTUDIO_DATA_DIR` / `RAGSTUDIO_CONFIG`, then drive the page over CDP (`Page.captureScreenshot`). Radix controls
  need the full pointer event sequence (pointerdown/mousedown/pointerup/mouseup/click), not just `.click()`.
- zsh does not word-split `$PY -m ragstudio`: use `./rs`.
- `sqlite3.Connection.executescript` commits implicitly, so migrations carry `BEGIN; … COMMIT;` in the script text.
- numpy on macOS arm64 emits spurious `matmul` RuntimeWarnings with float64; the affected spots use `np.errstate`.
- `x.get("k") or default` treats 0 as missing. Validate numeric config with explicit `is not None` checks.
- The mock embedding is a 96-dim hashed bag of words: good enough for plumbing, too coarse for semantic claims.
  Tests that need a specific passage retrieved should use `retrieval_mode="bm25"`.
- Mock results validate plumbing only. The first real run (OpenAI, 2026-10-12, one question without gold) was made
  by the user from the app; the test-suite itself never calls a real provider.
- A runbook can hold hundreds of runs per question (the first real one had 960). Any screen listing runs must
  filter, group and page; never lay runs out as side-by-side columns (Compare › By question is a table with facets,
  grouping by technique or identical answer, and at most 4 pinned answers side by side).
- Optional packages are checked before a runbook exists: `rerankers.missing_dependency` / `stores.missing_dependency`
  feed `runbook.normalize` (ValidationError naming the `pip install`) and `experiments options` (the UI disables the
  choice). Add new optional rerankers/stores to their `REQUIRES` map.
- `sentence-transformers` must be installed together with Docling's pins (`transformers==4.57.6`,
  `huggingface_hub==0.36.2` in `environment.yml`); installing it alone breaks Docling 2.64.
- `faiss-cpu` and `torch` each bundle `libomp`; importing both aborts the interpreter on macOS (OMP error 15) with
  no result line. The runbook rejects `store: faiss` + `cross_encoder`, and both lazy imports refuse the second
  library. Never set `KMP_DUPLICATE_LIB_OK`.
- The project lives in Dropbox: keep `Dados/` contents out of git and expect sync delays on large index files.
