import { parseList, parseNumbers } from '@/lib/format'
import type { TechniqueInfo } from '@/lib/types'

export interface ChunkRow {
  strategy: string
  size: string
  overlap: string
  parent: string
}

/** Editable form state. List fields stay as comma-separated text while typing. */
export interface Draft {
  name: string
  description: string
  corpus: string
  split: string
  questionSet: string
  limit: string
  techniques: string[]
  /** technique -> param -> text (possibly several comma-separated values). */
  params: Record<string, Record<string, string>>
  chunking: ChunkRow[]
  enrich: string[]
  store: string
  modes: string[]
  rerankers: string[]
  k: string
  seeds: string
  llms: string
  embeddings: string
  language: string
  maxContext: string
  temperature: string
  judge: boolean
  judgeModel: string
  budget: string
}

export const STRATEGIES = [
  'fixed',
  'recursive',
  'sentence',
  'semantic',
  'markdown_headers',
  'parent_child'
]
export const MODES = ['dense', 'bm25', 'hybrid', 'rrf', 'mmr']
export const RERANKERS = ['none', 'lexical', 'llm', 'cross_encoder']
export const STORES = ['memory', 'duckdb', 'faiss', 'chroma']

export function emptyDraft(defaults: {
  k?: string
  seed?: string
  language?: string
  maxContext?: string
  mode?: string
}): Draft {
  return {
    name: '',
    description: '',
    corpus: '',
    split: 'none',
    questionSet: '',
    limit: '',
    techniques: ['naive'],
    params: {},
    chunking: [{ strategy: 'fixed', size: '1000', overlap: '150', parent: '1500' }],
    enrich: ['none'],
    store: 'memory',
    modes: [defaults.mode || 'dense'],
    rerankers: ['none'],
    k: defaults.k || '5',
    seeds: defaults.seed || '42',
    llms: '',
    embeddings: '',
    language: defaults.language || 'pt',
    maxContext: defaults.maxContext || '6000',
    temperature: '0',
    judge: false,
    judgeModel: '',
    budget: ''
  }
}

export type BuildError =
  | {
      key:
        | 'err.name'
        | 'err.corpus'
        | 'err.questions'
        | 'err.techniques'
        | 'err.k'
        | 'err.seeds'
        | 'err.chunking'
    }
  | { key: 'err.param'; vars: { param: string; technique: string } }

export type Built =
  { ok: true; config: Record<string, unknown>; runs: number } | { ok: false; error: BuildError }

function parseParam(text: string, fallback: unknown): unknown[] | null {
  const raw = text.trim()
  if (raw === '') return []
  if (typeof fallback === 'boolean') {
    const out = parseList(raw).map((v) => v.toLowerCase())
    return out.every((v) => v === 'true' || v === 'false') ? out.map((v) => v === 'true') : null
  }
  if (typeof fallback === 'number') return parseNumbers(raw)
  return parseList(raw)
}

/** Draft -> runbook configuration accepted by `experiments preview|create`, plus the local run count. */
export function buildConfig(
  d: Draft,
  catalog: TechniqueInfo[],
  effective: { corpus: string; questionSet: string }
): Built {
  if (!d.name.trim()) return { ok: false, error: { key: 'err.name' } }
  if (!effective.corpus) return { ok: false, error: { key: 'err.corpus' } }
  if (!effective.questionSet) return { ok: false, error: { key: 'err.questions' } }
  if (d.techniques.length === 0) return { ok: false, error: { key: 'err.techniques' } }

  const k = parseNumbers(d.k)
  if (!k || k.length === 0 || k.some((v) => !Number.isInteger(v) || v <= 0))
    return { ok: false, error: { key: 'err.k' } }
  const seeds = parseNumbers(d.seeds)
  if (!seeds || seeds.length === 0 || seeds.some((v) => !Number.isInteger(v)))
    return { ok: false, error: { key: 'err.seeds' } }

  const chunking: Record<string, unknown>[] = []
  for (const row of d.chunking) {
    const size = Number(row.size)
    const overlap = Number(row.overlap)
    if (!Number.isFinite(size) || !Number.isFinite(overlap) || row.size.trim() === '')
      return { ok: false, error: { key: 'err.chunking' } }
    const entry: Record<string, unknown> = { strategy: row.strategy, size, overlap }
    if (row.strategy === 'parent_child') entry.parent_size = Number(row.parent) || 1500
    chunking.push(entry)
  }

  let techniqueCombos = 0
  const techniques: Record<string, unknown>[] = []
  for (const name of d.techniques) {
    const spec = catalog.find((x) => x.name === name)
    const params: Record<string, unknown> = {}
    const grid: Record<string, unknown[]> = {}
    let combos = 1
    for (const [param, fallback] of Object.entries(spec?.params ?? {})) {
      const text = d.params[name]?.[param]
      if (text === undefined) continue
      const values = parseParam(text, fallback)
      if (values === null)
        return { ok: false, error: { key: 'err.param', vars: { param, technique: name } } }
      if (values.length === 1) params[param] = values[0]
      else if (values.length > 1) {
        grid[param] = values
        combos *= values.length
      }
    }
    techniqueCombos += combos
    const entry: Record<string, unknown> = { name }
    if (Object.keys(params).length) entry.params = params
    if (Object.keys(grid).length) entry.grid = grid
    techniques.push(entry)
  }

  const llms = parseList(d.llms)
  const embeddings = parseList(d.embeddings)
  const enrich = d.enrich.map((e) => (e === 'none' ? null : e))
  const config: Record<string, unknown> = {
    name: d.name.trim(),
    description: d.description.trim(),
    corpus: effective.corpus,
    question_set: effective.questionSet,
    techniques,
    chunking,
    k,
    seeds,
    retrieval_modes: d.modes,
    rerankers: d.rerankers,
    enrich,
    store: d.store,
    language: d.language,
    max_context_chars: Number(d.maxContext) || 6000,
    temperature: Number(d.temperature) || 0,
    evaluation: { judge: d.judge, judge_model: d.judgeModel.trim() || null }
  }
  if (d.split !== 'none') config.split = d.split
  if (llms.length) config.llms = llms
  if (embeddings.length) config.embedding_models = embeddings
  if (d.limit.trim() && Number(d.limit) > 0) config.limit_questions = Math.floor(Number(d.limit))
  if (d.budget.trim() && Number.isFinite(Number(d.budget))) config.max_budget_usd = Number(d.budget)

  const runs =
    techniqueCombos *
    chunking.length *
    enrich.length *
    d.modes.length *
    d.rerankers.length *
    k.length *
    seeds.length *
    Math.max(1, llms.length) *
    Math.max(1, embeddings.length)
  return { ok: true, config, runs }
}

/** Apply a backend preset (`experiments presets`) on top of a draft. */
export function applyPreset(
  d: Draft,
  preset: Record<string, unknown>,
  catalog: TechniqueInfo[]
): Draft {
  const next = { ...d }
  const techniques = preset.techniques
  if (techniques === 'all') next.techniques = catalog.map((x) => x.name)
  else if (Array.isArray(techniques)) next.techniques = techniques.map(String)
  if (Array.isArray(preset.k)) next.k = preset.k.join(', ')
  if (Array.isArray(preset.seeds)) next.seeds = preset.seeds.join(', ')
  if (Array.isArray(preset.retrieval_modes)) next.modes = preset.retrieval_modes.map(String)
  return next
}
