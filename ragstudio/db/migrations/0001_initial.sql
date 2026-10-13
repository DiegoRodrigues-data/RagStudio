-- RagStudio schema v1. Never edit an applied migration: add a new numbered file.
-- executescript() commits implicitly, so the transaction is written in the script itself.
BEGIN;

CREATE TABLE schema_version (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL);
CREATE TABLE maintenance (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO maintenance VALUES ('allow_delete', '0');

-- ------------------------------------------------------------------ corpus
CREATE TABLE corpora (
    id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT '', source_path TEXT NOT NULL DEFAULT '', content_hash TEXT NOT NULL,
    cleaning TEXT NOT NULL DEFAULT '[]', profile TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);

CREATE TABLE documents (
    corpus_id TEXT NOT NULL REFERENCES corpora(id) ON DELETE CASCADE, doc_id TEXT NOT NULL,
    source_path TEXT NOT NULL DEFAULT '', sha256 TEXT NOT NULL, format TEXT NOT NULL, language TEXT NOT NULL DEFAULT '',
    chars INTEGER NOT NULL, pages INTEGER, text TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
    profile TEXT NOT NULL DEFAULT '{}', PRIMARY KEY (corpus_id, doc_id));

CREATE TABLE corpus_splits (
    corpus_id TEXT NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    split TEXT NOT NULL CHECK (split IN ('train', 'validation', 'test')),
    document_ids TEXT NOT NULL, split_hash TEXT NOT NULL, seed INTEGER, created_at TEXT NOT NULL,
    PRIMARY KEY (corpus_id, split));

CREATE TABLE indices (
    index_hash TEXT PRIMARY KEY, corpus_id TEXT NOT NULL REFERENCES corpora(id), split TEXT,
    chunking TEXT NOT NULL, embedding_model TEXT NOT NULL, embedding_provider TEXT NOT NULL, store TEXT NOT NULL,
    enrich TEXT, dim INTEGER NOT NULL, chunks INTEGER NOT NULL, documents INTEGER NOT NULL, path TEXT NOT NULL,
    chunking_profile TEXT NOT NULL DEFAULT '{}', build_usage TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);

-- --------------------------------------------------------------- questions
CREATE TABLE question_sets (
    id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);

CREATE TABLE questions (
    id TEXT PRIMARY KEY, set_id TEXT NOT NULL REFERENCES question_sets(id) ON DELETE CASCADE, code TEXT NOT NULL,
    text TEXT NOT NULL, expected_answer TEXT,
    answer_type TEXT NOT NULL DEFAULT 'extraction'
        CHECK (answer_type IN ('boolean', 'extraction', 'classification', 'reasoning', 'summarization')),
    split TEXT CHECK (split IS NULL OR split IN ('train', 'validation', 'test')),
    metadata TEXT NOT NULL DEFAULT '{}', version INTEGER NOT NULL DEFAULT 1,
    supersedes_id TEXT REFERENCES questions(id), archived_at TEXT, created_at TEXT NOT NULL);
CREATE INDEX idx_questions_set ON questions(set_id, code);

CREATE TABLE gold_passages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    document_id TEXT NOT NULL, text TEXT NOT NULL, char_start INTEGER, char_end INTEGER,
    source TEXT NOT NULL DEFAULT 'imported' CHECK (source IN ('manual', 'imported', 'llm_suggested')));
CREATE INDEX idx_gold_question ON gold_passages(question_id);

-- ------------------------------------------------------------- experiments
CREATE TABLE runbooks (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', config TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'budget_exceeded')),
    max_budget_usd REAL, estimate TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, started_at TEXT,
    finished_at TEXT);

CREATE TABLE runs (
    id TEXT PRIMARY KEY, runbook_id TEXT NOT NULL REFERENCES runbooks(id) ON DELETE CASCADE, seq INTEGER NOT NULL,
    technique TEXT NOT NULL, technique_version TEXT NOT NULL DEFAULT '', config TEXT NOT NULL,
    config_hash TEXT NOT NULL, index_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    error TEXT, replicates_run_id TEXT REFERENCES runs(id), cost_usd REAL, started_at TEXT, finished_at TEXT,
    UNIQUE (runbook_id, seq));
CREATE INDEX idx_runs_runbook ON runs(runbook_id, seq);
CREATE INDEX idx_runs_hash ON runs(config_hash);

CREATE TABLE query_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL, question_code TEXT NOT NULL, question_text TEXT NOT NULL, answer TEXT NOT NULL,
    context_text TEXT NOT NULL, context_chars INTEGER NOT NULL, context_truncated INTEGER NOT NULL DEFAULT 0,
    citations TEXT NOT NULL DEFAULT '[]', diagnostics TEXT NOT NULL DEFAULT '{}', timings TEXT NOT NULL DEFAULT '[]',
    usage TEXT NOT NULL DEFAULT '{}', latency_total REAL NOT NULL DEFAULT 0, llm_calls INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0, completion_tokens INTEGER NOT NULL DEFAULT 0,
    embedding_tokens INTEGER NOT NULL DEFAULT 0, cost_usd REAL, warnings TEXT NOT NULL DEFAULT '[]', error TEXT,
    created_at TEXT NOT NULL, UNIQUE (run_id, question_id));
CREATE INDEX idx_qr_run ON query_results(run_id);
CREATE INDEX idx_qr_question ON query_results(question_id);

CREATE TABLE retrieved_chunks (
    query_result_id INTEGER NOT NULL REFERENCES query_results(id) ON DELETE CASCADE, rank INTEGER NOT NULL,
    chunk_id TEXT NOT NULL, document_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, score REAL NOT NULL,
    source TEXT NOT NULL, char_start INTEGER NOT NULL, char_end INTEGER NOT NULL, in_context INTEGER NOT NULL DEFAULT 1,
    text TEXT NOT NULL, PRIMARY KEY (query_result_id, rank));

-- ------------------------------------------------------------------ metrics
-- Append-only: a re-evaluation writes rows with a higher eval_version, it never overwrites.
CREATE TABLE retrieval_metrics (
    query_result_id INTEGER NOT NULL REFERENCES query_results(id) ON DELETE CASCADE, eval_version INTEGER NOT NULL,
    k INTEGER NOT NULL, gold_count INTEGER NOT NULL, hit REAL, recall REAL, precision REAL, mrr REAL, ndcg REAL,
    context_coverage REAL, created_at TEXT NOT NULL, PRIMARY KEY (query_result_id, eval_version));

CREATE TABLE generation_metrics (
    query_result_id INTEGER NOT NULL REFERENCES query_results(id) ON DELETE CASCADE, eval_version INTEGER NOT NULL,
    exact_match REAL, f1 REAL, accuracy REAL, faithfulness REAL, groundedness REAL, citation_accuracy REAL,
    hallucination REAL, refusal REAL, judge_accuracy REAL, judge_faithfulness REAL, judge_model TEXT,
    judge_prompt_sha256 TEXT, created_at TEXT NOT NULL, PRIMARY KEY (query_result_id, eval_version));

CREATE TABLE run_metrics (
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, eval_version INTEGER NOT NULL,
    metrics TEXT NOT NULL, availability TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, eval_version));

CREATE TABLE answer_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT, query_result_id INTEGER NOT NULL REFERENCES query_results(id) ON DELETE CASCADE,
    reviewer TEXT NOT NULL, verdict TEXT NOT NULL CHECK (verdict IN ('correct', 'partially', 'incorrect')),
    note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);

-- ----------------------------------------------------------------- evidence
CREATE TABLE evidence_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('info', 'request', 'response', 'retrieval', 'evaluation', 'retry', 'error')),
    question_id TEXT, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, prev_sha256 TEXT NOT NULL,
    chain_sha256 TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE (run_id, seq));

CREATE TABLE prompts (
    sha256 TEXT PRIMARY KEY, task TEXT NOT NULL, language TEXT NOT NULL, system TEXT NOT NULL, template TEXT NOT NULL,
    version TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE environment_snapshots (
    run_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE, python_version TEXT NOT NULL, platform TEXT NOT NULL,
    packages TEXT NOT NULL, git_commit TEXT, ragstudio_version TEXT NOT NULL, llm TEXT NOT NULL, embedder TEXT NOT NULL,
    seed INTEGER, created_at TEXT NOT NULL);

CREATE TABLE exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, ref TEXT NOT NULL DEFAULT '', format TEXT NOT NULL,
    path TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, runbook_id TEXT, level TEXT NOT NULL, message TEXT NOT NULL,
    created_at TEXT NOT NULL);

-- ------------------------------------------------------------- immutability
-- Results and evidence of a completed run cannot change. Deletion is only possible through the guarded
-- runbook deletion, which raises maintenance.allow_delete inside its transaction.
CREATE TRIGGER trg_qr_no_update BEFORE UPDATE ON query_results
WHEN (SELECT status FROM runs WHERE id = OLD.run_id) = 'completed'
BEGIN SELECT RAISE(ABORT, 'query_results of a completed run are immutable'); END;

CREATE TRIGGER trg_qr_no_delete BEFORE DELETE ON query_results
WHEN (SELECT status FROM runs WHERE id = OLD.run_id) = 'completed'
     AND (SELECT value FROM maintenance WHERE key = 'allow_delete') <> '1'
BEGIN SELECT RAISE(ABORT, 'query_results of a completed run are immutable'); END;

CREATE TRIGGER trg_rc_no_update BEFORE UPDATE ON retrieved_chunks
BEGIN SELECT RAISE(ABORT, 'retrieved_chunks are immutable'); END;

CREATE TRIGGER trg_rc_no_delete BEFORE DELETE ON retrieved_chunks
WHEN (SELECT r.status FROM runs r JOIN query_results q ON q.run_id = r.id WHERE q.id = OLD.query_result_id) = 'completed'
     AND (SELECT value FROM maintenance WHERE key = 'allow_delete') <> '1'
BEGIN SELECT RAISE(ABORT, 'retrieved_chunks of a completed run are immutable'); END;

CREATE TRIGGER trg_ev_no_update BEFORE UPDATE ON evidence_events
BEGIN SELECT RAISE(ABORT, 'evidence_events are append-only'); END;

CREATE TRIGGER trg_ev_no_delete BEFORE DELETE ON evidence_events
WHEN (SELECT status FROM runs WHERE id = OLD.run_id) = 'completed'
     AND (SELECT value FROM maintenance WHERE key = 'allow_delete') <> '1'
BEGIN SELECT RAISE(ABORT, 'evidence_events of a completed run are immutable'); END;

CREATE TRIGGER trg_rm_no_update BEFORE UPDATE ON retrieval_metrics
BEGIN SELECT RAISE(ABORT, 'retrieval_metrics are append-only (write a new eval_version)'); END;

CREATE TRIGGER trg_gm_no_update BEFORE UPDATE ON generation_metrics
BEGIN SELECT RAISE(ABORT, 'generation_metrics are append-only (write a new eval_version)'); END;

CREATE TRIGGER trg_run_config_frozen BEFORE UPDATE OF config, config_hash, technique, index_hash ON runs
WHEN OLD.status = 'completed'
BEGIN SELECT RAISE(ABORT, 'a completed run cannot be reconfigured'); END;

COMMIT;
