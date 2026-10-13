/** Shapes returned by the Python backend (`python -m ragstudio ...`). Field names match the JSON. */

export type Dict = Record<string, unknown>

export interface DbStatus {
  database: string
  version: number
  pending: number[]
  counts: Record<string, number>
}

export type ConfigData = Record<string, Record<string, string>>

export interface NumericSummary {
  min: number
  max: number
  mean: number
  median: number
  stdev: number
}

export interface CorpusProfile {
  documents: number
  total_chars: number
  total_words: number
  chars: NumericSummary
  words: NumericSummary
  formats: Record<string, number>
  languages: Record<string, number>
  avg_table_line_ratio: number
  avg_digit_ratio: number
}

export interface CorpusSummary {
  id: string
  name: string
  documents: number
  language: string
  total_chars: number | null
  created_at: string
}

export interface DocumentRow {
  doc_id: string
  chars: number
  format: string
  language: string
  sha256: string
}

export interface CorpusDetail {
  id: string
  name: string
  description: string
  language: string
  source_path: string
  content_hash: string
  cleaning: string[]
  profile: CorpusProfile
  created_at: string
  splits: Record<string, number>
  split_documents: Record<string, string[]>
  indices: string[]
  documents: DocumentRow[]
}

export interface DocumentProfile {
  doc_id: string
  chars: number
  words: number
  lines: number
  paragraphs: number
  headings: number
  avg_paragraph_chars: number
  table_line_ratio: number
  list_line_ratio: number
  digit_ratio: number
  vocabulary_ratio: number
  language: string
  format: string
  pages: number | null
}

export interface CorpusProfileData {
  corpus: CorpusProfile
  documents: DocumentProfile[]
}

export interface DocumentDetail {
  corpus: string
  doc_id: string
  source_path: string
  sha256: string
  format: string
  language: string
  chars: number
  pages: number | null
  text: string
  metadata: Dict
  profile: DocumentProfile
}

export interface ChunkingConfig {
  strategy: string
  size: number
  overlap: number
  parent_size?: number
}

export interface IndexRow {
  index_hash: string
  corpus_id: string
  split: string | null
  chunking: ChunkingConfig
  embedding_model: string
  embedding_provider?: string
  store: string
  enrich: string | null
  dim: number
  chunks: number
  documents: number
  created_at: string
  path?: string
  chunking_profile?: Record<string, number>
  build_usage?: Record<string, number>
}

export interface SearchHit {
  rank: number
  score: number
  source: string
  chunk_id: string
  char_start: number
  char_end: number
  text: string
}

export type TechniqueStatus = 'implemented' | 'prototype' | 'adapter' | 'mock' | 'pending'

export interface TechniqueInfo {
  name: string
  /** Display name; `name` is the stable identifier stored with runs. */
  title: string
  /** Pipeline stage where the technique acts: indexing | query | retrieval | post_retrieval | orchestration. */
  stage: string
  /** Run settings the technique replaces with its own (retrieval_mode, reranker, max_context_chars). */
  ignores: string[]
  requires: string[]
  version: string
  family: string
  status: TechniqueStatus
  description: string
  params: Record<string, unknown>
  reference: string
}

export interface QuestionSetSummary {
  id: string
  name: string
  description: string
  language: string
  questions: number
  created_at: string
}

export interface GoldPassage {
  document_id: string
  text: string
  char_start: number | null
  char_end: number | null
  source?: string
}

export interface Question {
  id: string
  set_id: string
  code: string
  text: string
  expected_answer: string | null
  answer_type: string
  split: string | null
  metadata: Dict
  version: number
  supersedes_id: string | null
  archived_at: string | null
  created_at: string
  gold_passages: GoldPassage[]
}

export interface QuestionSetDetail {
  set: QuestionSetSummary
  questions: Question[]
}

export interface Availability {
  questions: number
  with_gold_passages: number
  with_expected_answer: number
  available: string[]
  partial: Record<string, string>
  requires_annotation: Record<string, string>
}

export interface RunbookSummary {
  id: string
  name: string
  description: string
  status: string
  max_budget_usd: number | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  runs: number
  completed: number
  cost_usd: number | null
}

export interface Estimate {
  runs: number
  questions_per_run: number
  answers: number
  lower_bound: boolean
  prompt_tokens: number
  completion_tokens: number
  cost_usd: number | null
  note: string
}

export interface PreviewResult {
  config: Dict
  runs: number
  estimate: Estimate
  corpus: string
  documents: number
  questions: number
  techniques: string[]
  duplicate_configs: number
  pruned: PrunedReport
}

/** Grid combinations the runbook skipped: redundant (ignored axis) or incompatible (missing index). */
export interface PrunedReport {
  enabled: boolean
  full_grid: number
  runs: number
  redundant: number
  incompatible: number
  without_runs: string[]
  by_technique: {
    technique: string
    runs: number
    redundant: number
    incompatible: number
    ignores: string[]
    needs: string[]
  }[]
}

export interface RunStatusRow {
  id: string
  seq: number
  technique: string
  status: string
  error: string | null
  cost_usd: number | null
  config_hash: string
  replicates_run_id: string | null
  recall: number | null
  mrr: number | null
  f1: number | null
  faithfulness: number | null
  latency_mean: number | null
  llm_calls_per_question: number | null
}

export interface RunbookStatus {
  id: string
  name: string
  status: string
  estimate: Estimate
  max_budget_usd: number | null
  runs: RunStatusRow[]
}

/** One row per completed run: configuration columns + aggregated metrics (dynamic keys). */
export interface RunTableRow {
  runbook_id: string
  runbook: string
  run_id: string
  seq: number
  technique: string
  retrieval_mode: string
  reranker: string
  k: number
  seed: number
  llm: string | null
  embedding_model: string | null
  chunking: string
  params: string
  config_hash: string
  index_hash: string | null
  [metric: string]: unknown
}

export interface GroupRow {
  runs: number
  [key: string]: unknown
}

export interface RunConfig {
  technique: string
  technique_version: string
  params: Dict
  corpus: string
  split: string | null
  question_set: string
  chunking: ChunkingConfig
  embedding_model: string | null
  llm: string | null
  k: number
  seed: number
  retrieval_mode: string
  reranker: string
  enrich: string | null
  store: string
  language: string
  max_context_chars: number
  provider: string
  [key: string]: unknown
}

export interface RunAnswerRow {
  id: number
  question: string
  text: string
  answer: string
  latency: number
  llm_calls: number
  warnings: string[]
  error: string | null
}

export interface RunDetail {
  run: {
    id: string
    technique: string
    technique_version: string
    status: string
    error: string | null
    config: RunConfig
    config_hash: string
    index_hash: string | null
    cost_usd: number | null
    started_at: string | null
    finished_at: string | null
  }
  metrics: Dict | null
  availability: Availability | null
  environment: Dict | null
  evidence: { ok: boolean; events: number; head?: string; broken_at_seq?: number }
  answers: RunAnswerRow[]
}

export interface RetrievedChunkRow {
  rank: number
  chunk_id: string
  document_id: string
  chunk_index: number
  score: number
  source: string
  char_start: number
  char_end: number
  in_context: number
  text: string
}

export interface AnswerDetail {
  result: {
    id: number
    run_id: string
    question_id: string
    question_code: string
    question_text: string
    answer: string
    context_text: string
    context_chars: number
    context_truncated: number
    citations: Dict[]
    diagnostics: Dict
    timings: { stage: string; seconds: number }[]
    usage: Dict
    latency_total: number
    llm_calls: number
    prompt_tokens: number
    completion_tokens: number
    cost_usd: number | null
    warnings: string[]
    error: string | null
  }
  chunks: RetrievedChunkRow[]
  metrics: Dict | null
  question: Question | null
  run: { id: string; technique: string; config: RunConfig; status: string }
}

export interface EvidenceEvent {
  seq: number
  kind: string
  question_id: string | null
  payload: Dict
  payload_sha256: string
  chain_sha256: string
  created_at: string
}

export interface EvidencePage {
  run_id: string
  total: number
  chain: { ok: boolean; events: number; head?: string; broken_at_seq?: number }
  events: EvidenceEvent[]
}

export interface ReevalResult {
  run_id: string
  eval_version: number
  metrics: Dict
  judge: string | null
}

export interface PairedStat {
  n: number
  mean_a?: number
  mean_b?: number
  mean_diff?: number
  ci95?: [number, number]
  t?: { statistic: number | null; p_value: number; df: number }
  wilcoxon?: { statistic: number; p_value: number; n_nonzero: number; approximation: string }
  permutation_p?: number
  permutation_p_holm?: number
  cohens_dz?: number | null
  note?: string
}

export interface PairedComparison {
  run_a: string
  run_b: string
  technique_a: string
  technique_b: string
  config_diff: Record<string, { a: unknown; b: unknown }>
  common_questions: number
  metrics: Record<string, PairedStat>
  note: string
}

/** `experiments options`: choices that depend on optional Python packages. */
export interface RunbookOption {
  name: string
  available: boolean
  /** pip package to install when `available` is false. */
  requires: string | null
}

export interface RunbookOptions {
  rerankers: RunbookOption[]
  stores: RunbookOption[]
}

export interface AnswerCell {
  result_id: number
  run_id: string
  seq: number
  technique: string
  retrieval_mode: string
  reranker: string
  k: number
  chunking: string
  params: string
  answer: string
  error: string | null
  warnings: string[]
  latency_total: number
  llm_calls: number
  context_chars: number
  recall: number | null
  mrr: number | null
  f1: number | null
  accuracy: number | null
  faithfulness: number | null
  context_coverage: number | null
  hallucination: number | null
}

export interface QuestionAnswers {
  question_id: string
  code: string
  text: string
  expected_answer: string | null
  gold_passages: GoldPassage[]
  answers: AnswerCell[]
}

export interface Correlation {
  technique: string
  metric: string
  feature: string
  spearman: number
  n: number
  documents: number
}

export interface CharacteristicsAnalysis {
  rows: number
  documents: number
  target_sources: Record<string, number>
  correlations: Correlation[]
  size_bins: Dict[]
  by_language: Dict[]
  by_format: Dict[]
  by_corpus: Dict[]
  note: string
}

export interface FigureFile {
  caption: string
  png: string
  svg: string
  pdf: string
}

export interface FiguresResult {
  directory: string
  figures: FigureFile[]
  skipped: string[]
}

export interface ExportRow {
  id: number
  kind: string
  ref: string
  format: string
  path: string
  sha256: string
  created_at: string
}

/** Progress events of `experiments run --stream` and `index build --stream` (wrapped as `{progress}`). */
export interface ProgressPayload {
  event: string
  run_id?: string
  runbook_id?: string
  technique?: string
  position?: number
  of?: number
  runs?: number
  question?: string
  failed?: boolean
  latency?: number
  status?: string
  error?: string
  spent_usd?: number
  budget_usd?: number
  cost_usd?: number | null
  index_reused?: boolean
  done?: number
  total?: number
  name?: string
  ok?: boolean
  chunks?: number
  documents?: number
  completed?: number
  skipped?: number
  cancelled?: number
  reason?: string
  [key: string]: unknown
}

export interface ProgressEvent {
  progress: ProgressPayload
}

export type ReferenceKind = 'guide' | 'technique' | 'component' | 'metric' | 'statistic' | 'concept'

export interface ReferenceSource {
  authors: string
  year: number | null
  title: string
  venue: string
  url: string
  /** Date the link was last resolved; null when it was never confirmed. */
  checked: string | null
}

export interface ReferenceParam {
  name: string
  default: unknown
  help: string
  choices: unknown[] | null
}

/** Kind-specific facts: metrics fill keys/needs/better/range, techniques status..params, components package. */
export interface ReferenceFacts {
  identifier?: string
  stage?: string
  ignores?: string[]
  keys?: string[]
  needs?: 'none' | 'gold' | 'expected' | 'judge' | 'judge+expected' | 'human'
  better?: 'higher' | 'lower' | 'context'
  range?: 'unit' | 'binary' | 'seconds' | 'count' | 'usd' | 'chars'
  status?: TechniqueStatus
  version?: string
  family?: string
  requires?: string[]
  calls?: string | null
  params?: ReferenceParam[]
  package?: string
  files?: string[]
}

export interface ReferenceEntry {
  id: string
  kind: ReferenceKind
  group: string
  name: string
  summary: string
  sections: { key: string; text: string }[]
  facts: ReferenceFacts
  sources: string[]
  related: string[]
}

export interface ReferenceCatalog {
  language: string
  kinds: ReferenceKind[]
  groups: Record<string, string>
  entries: ReferenceEntry[]
  sources: Record<string, ReferenceSource>
}
