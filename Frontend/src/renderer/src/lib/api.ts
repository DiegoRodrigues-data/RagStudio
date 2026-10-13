/**
 * Typed client for the Python backend CLI.
 *
 * CLI convention: `python -m ragstudio <group> <command> [--flag value ...]`
 *  - flags are kebab-case (`runId` -> `--run-id`)
 *  - `true` booleans become bare flags, `false`/`undefined`/`null` are omitted
 *  - arrays and objects are passed as a single JSON string
 *
 * Every non-streaming wrapper returns `Promise<ApiResult<T>>` and never throws.
 * Streaming wrappers take a `streamId` first; progress arrives through `window.api.onProgress`
 * (see `useStream`) as `{ progress: {...} }` events.
 */
import type { ApiResult } from './api-types'
import type {
  AnswerDetail,
  CharacteristicsAnalysis,
  ConfigData,
  CorpusDetail,
  CorpusProfileData,
  CorpusSummary,
  DbStatus,
  DocumentDetail,
  EvidencePage,
  ExportRow,
  FiguresResult,
  GroupRow,
  IndexRow,
  PairedComparison,
  PreviewResult,
  QuestionAnswers,
  ReferenceCatalog,
  QuestionSetDetail,
  QuestionSetSummary,
  ReevalResult,
  RunDetail,
  RunTableRow,
  RunbookStatus,
  RunbookSummary,
  SearchHit,
  TechniqueInfo,
  Availability,
  RunbookOptions
} from './types'

export type Flags = Record<string, unknown>

export function toKebab(key: string): string {
  return key
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/_/g, '-')
    .toLowerCase()
}

export function flagsToArgv(flags: Flags = {}): string[] {
  const out: string[] = []
  for (const [key, value] of Object.entries(flags)) {
    if (value === undefined || value === null || value === false || value === '') continue
    const flag = `--${toKebab(key)}`
    if (value === true) out.push(flag)
    else if (typeof value === 'object') out.push(flag, JSON.stringify(value))
    else out.push(flag, String(value))
  }
  return out
}

export function buildArgv(group: string, command: string, flags?: Flags): string[] {
  return [group, command, ...flagsToArgv(flags)]
}

function bridge(): Window['api'] | undefined {
  return typeof window !== 'undefined' ? window.api : undefined
}

export async function call<T = unknown>(
  group: string,
  command: string,
  flags?: Flags
): Promise<ApiResult<T>> {
  const api = bridge()
  if (!api) return { ok: false, error: 'IPC bridge (window.api) is not available' }
  try {
    return (await api.run(buildArgv(group, command, flags))) as ApiResult<T>
  } catch (e) {
    return { ok: false, error: (e as Error).message ?? String(e) }
  }
}

export async function stream(
  streamId: string,
  group: string,
  command: string,
  flags?: Flags
): Promise<void> {
  const api = bridge()
  if (!api) throw new Error('IPC bridge (window.api) is not available')
  await api.stream(streamId, [...buildArgv(group, command, flags), '--stream'])
}

export async function cancelStream(streamId: string): Promise<void> {
  await bridge()?.cancelStream(streamId)
}

const ids = (xs: string[]): string => xs.join(',')

export const db = {
  status: () => call<DbStatus>('db', 'status'),
  migrate: () => call('db', 'migrate'),
  backup: (output?: string) => call<{ path: string }>('db', 'backup', { output }),
  integrityCheck: () =>
    call<{ ok: boolean; integrity: string[]; foreign_key_violations: number }>(
      'db',
      'integrity-check'
    )
}

export const config = {
  show: () => call<ConfigData>('config', 'show'),
  setMany: (values: Record<string, Record<string, string>>) =>
    call<{ saved: string; changed: number; config: ConfigData }>('config', 'set-many', {
      json: values
    }),
  testConnection: () =>
    call<{
      ok: boolean
      provider: string
      embedding: { ok: boolean; model?: string; dim?: number; error?: string }
      llm: { ok: boolean; model?: string; reply?: string; error?: string }
    }>('config', 'test-connection'),
  listModels: () => call<{ provider: string; models: string[] }>('config', 'list-models')
}

export interface CorpusImportOptions {
  path: string
  name: string
  format?: string
  language?: string
  clean?: string
  description?: string
}

export const corpus = {
  list: () => call<CorpusSummary[]>('corpus', 'list'),
  describe: (name: string) => call<CorpusDetail>('corpus', 'describe', { name }),
  profile: (name: string) => call<CorpusProfileData>('corpus', 'profile', { name }),
  document: (name: string, docId: string) =>
    call<DocumentDetail>('corpus', 'document', { name, docId }),
  /** Streaming: one `file_started` / `file` event per file (PDF conversion takes seconds per document). */
  import: (streamId: string, opts: CorpusImportOptions) =>
    stream(streamId, 'corpus', 'import', { ...opts }),
  split: (
    name: string,
    opts: { train: number; validation: number; test: number; seed: number; stratifyBy?: string }
  ) =>
    call<{ splits: Record<string, string[]>; split_hash: string }>('corpus', 'split', {
      name,
      ...opts
    }),
  assignSplits: (name: string, assign: Record<string, string[]>) =>
    call<{ splits: Record<string, string[]>; split_hash: string }>('corpus', 'split', {
      name,
      assign
    }),
  delete: (name: string) => call('corpus', 'delete', { name, confirm: name })
}

export interface IndexBuildOptions {
  corpus: string
  chunking: Record<string, unknown>
  embeddingModel?: string
  store?: string
  split?: string
  enrich?: string
  llm?: string
  force?: boolean
}

export const index = {
  list: (corpusName?: string) => call<IndexRow[]>('index', 'list', { corpus: corpusName }),
  describe: (hash: string) => call<IndexRow>('index', 'describe', { index: hash }),
  /** Streaming: chunked / embedded / enriched / persisted events. */
  build: (streamId: string, opts: IndexBuildOptions) =>
    stream(streamId, 'index', 'build', { ...opts }),
  search: (hash: string, query: string, mode: string, k: number) =>
    call<SearchHit[]>('index', 'search', { index: hash, query, mode, k, preview: 400 }),
  delete: (hash: string) => call('index', 'delete', { index: hash })
}

export const techniques = {
  list: () => call<TechniqueInfo[]>('techniques', 'list')
}

export const reference = {
  list: (language: 'pt' | 'en') => call<ReferenceCatalog>('reference', 'list', { language })
}

export const questions = {
  sets: () => call<QuestionSetSummary[]>('questions', 'list'),
  list: (set: string, includeArchived = false) =>
    call<QuestionSetDetail>('questions', 'list', { set, includeArchived }),
  importJson: (path: string, corpusName?: string, set?: string) =>
    call<{ id: string; name: string; questions: number }>('questions', 'import-json', {
      path,
      corpus: corpusName,
      set
    }),
  create: (payload: {
    set: string
    text: string
    code?: string
    expectedAnswer?: string
    answerType?: string
    split?: string
    goldPassages?: unknown[]
    corpus?: string
  }) => call<{ id: string; code: string }>('questions', 'create', payload),
  update: (payload: {
    id: string
    text?: string
    expectedAnswer?: string
    answerType?: string
    split?: string
    goldPassages?: unknown[]
    corpus?: string
  }) =>
    call<{ id: string; version: number; new_version_created: boolean }>(
      'questions',
      'update',
      payload
    ),
  archive: (id: string) => call('questions', 'archive', { id }),
  export: (set: string, output: string) =>
    call<{ path: string; questions: number }>('questions', 'export', { set, output }),
  availability: (questionSet: string, judge = false) =>
    call<Availability & { question_set: string }>('evaluate', 'availability', {
      questionSet,
      judge
    })
}

export const experiments = {
  presets: () => call<Record<string, Record<string, unknown>>>('experiments', 'presets'),
  options: () => call<RunbookOptions>('experiments', 'options'),
  preview: (cfg: Record<string, unknown>) =>
    call<PreviewResult>('experiments', 'preview', { config: cfg }),
  create: (cfg: Record<string, unknown>) =>
    call<{ id: string; name: string; runs: number }>('experiments', 'create', { config: cfg }),
  list: () => call<RunbookSummary[]>('experiments', 'list'),
  status: (id: string) => call<RunbookStatus>('experiments', 'status', { id }),
  /** Streaming. Completed runs are skipped; interrupted ones restart. */
  run: (streamId: string, id: string) => stream(streamId, 'experiments', 'run', { id }),
  cancel: (streamId: string) => cancelStream(streamId),
  show: (runId: string) => call<RunDetail>('experiments', 'show', { runId }),
  answer: (resultId: number) => call<AnswerDetail>('experiments', 'answer', { resultId }),
  evidence: (runId: string, questionId?: string, offset = 0, limit = 200) =>
    call<EvidencePage>('experiments', 'evidence', { runId, questionId, offset, limit }),
  reproduce: (runId: string, dryRun = false) =>
    call<Record<string, unknown>>('experiments', 'reproduce', { runId, dryRun }),
  verify: (id: string) =>
    call<{ ok: boolean; runs: Record<string, { ok: boolean; events: number }> }>(
      'experiments',
      'verify',
      { id }
    ),
  deletePreview: (id: string) =>
    call<{ runbook: string; runs: number; query_results: number; evidence_events: number }>(
      'experiments',
      'delete-preview',
      { id }
    ),
  delete: (id: string, confirm: string) =>
    call<{ deleted: boolean; backup: string }>('experiments', 'delete', { id, confirm })
}

export const evaluate = {
  rerun: (runId: string, judge?: boolean) =>
    call<ReevalResult>('evaluate', 'rerun', {
      runId,
      judge: judge === true,
      noJudge: judge === false
    }),
  reviewAdd: (resultId: number, verdict: string, note: string, reviewer = 'user') =>
    call<{ id: number }>('evaluate', 'review-add', { resultId, verdict, note, reviewer }),
  agreement: (runId: string) =>
    call<{ reviews: number; compared?: number; agreement: number | null }>(
      'evaluate',
      'agreement',
      {
        runId
      }
    )
}

export const compare = {
  table: (runbookIds: string[]) =>
    call<{ rows: RunTableRow[] }>('compare', 'table', { id: ids(runbookIds) }),
  group: (runbookIds: string[], by: string) =>
    call<{ by: string; groups: GroupRow[]; runs: number }>('compare', 'runbook', {
      id: ids(runbookIds),
      by
    }),
  runs: (runA: string, runB: string) =>
    call<PairedComparison>('compare', 'runs', { ids: `${runA},${runB}` }),
  answers: (runbookIds: string[]) =>
    call<QuestionAnswers[]>('compare', 'answers', { id: ids(runbookIds) }),
  characteristics: (runbookIds: string[]) =>
    call<CharacteristicsAnalysis>('compare', 'characteristics', { runbookId: ids(runbookIds) })
}

export const reports = {
  html: (runbookIds: string[], output?: string, title?: string) =>
    call<{ path: string; sha256: string; figures: number; skipped_figures: string[] }>(
      'reports',
      'html',
      { runbookIds: ids(runbookIds), output, title }
    ),
  figures: (runbookIds: string[], output?: string) =>
    call<FiguresResult>('reports', 'figures', { runbookIds: ids(runbookIds), output }),
  tables: (runbookIds: string[], format: string, by: string, output?: string) =>
    call<{ format: string; rows: number; text: string; path: string | null }>('reports', 'tables', {
      runbookIds: ids(runbookIds),
      format,
      by,
      output
    }),
  export: (runbookIds: string[], table: string, format: string, output?: string) =>
    call<{ table: string; format: string; rows: number; path: string; sha256: string }>(
      'reports',
      'export',
      { runbookIds: ids(runbookIds), table, format, output }
    ),
  list: () => call<ExportRow[]>('reports', 'list')
}

export const api = {
  call,
  stream,
  cancelStream,
  db,
  config,
  corpus,
  index,
  techniques,
  reference,
  questions,
  experiments,
  evaluate,
  compare,
  reports
}

export default api
