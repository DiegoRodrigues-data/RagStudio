/** Metric names (kept in English, as in reports), ordering and formatting shared by every page. */

export const METRIC_LABELS: Record<string, string> = {
  hit: 'Hit@k',
  recall: 'Recall@k',
  precision: 'Precision@k',
  mrr: 'MRR',
  ndcg: 'nDCG@k',
  context_coverage: 'Context coverage',
  exact_match: 'Exact match',
  f1: 'Token F1',
  accuracy: 'Accuracy',
  faithfulness: 'Faithfulness',
  groundedness: 'Groundedness',
  citation_accuracy: 'Citation accuracy',
  hallucination: 'Hallucination',
  refusal: 'Refusal',
  judge_accuracy: 'Judge accuracy',
  judge_faithfulness: 'Judge faithfulness',
  latency_mean: 'Latency',
  latency_total: 'Latency',
  llm_calls_per_question: 'LLM calls / question',
  llm_calls: 'LLM calls',
  prompt_tokens: 'Prompt tokens',
  completion_tokens: 'Completion tokens',
  embedding_tokens: 'Embedding tokens',
  cost_usd: 'Cost',
  context_chars_mean: 'Context chars',
  context_chars: 'Context chars'
}

export const RETRIEVAL_METRICS = ['recall', 'precision', 'mrr', 'ndcg', 'hit', 'context_coverage']
export const GENERATION_METRICS = [
  'f1',
  'accuracy',
  'exact_match',
  'faithfulness',
  'groundedness',
  'citation_accuracy',
  'hallucination',
  'refusal',
  'judge_accuracy',
  'judge_faithfulness'
]
export const EFFICIENCY_METRICS = [
  'latency_mean',
  'llm_calls_per_question',
  'prompt_tokens',
  'completion_tokens',
  'cost_usd',
  'context_chars_mean'
]
/** Columns shown by default in run tables. */
export const HEADLINE_METRICS = [
  'recall',
  'mrr',
  'f1',
  'faithfulness',
  'latency_mean',
  'llm_calls_per_question',
  'cost_usd'
]
export const ALL_METRICS = [...RETRIEVAL_METRICS, ...GENERATION_METRICS, ...EFFICIENCY_METRICS]

/** Bounded 0..1 scores (drawn on a fixed 0..1 scale). */
export const BOUNDED = new Set([...RETRIEVAL_METRICS, ...GENERATION_METRICS])

export const LOWER_IS_BETTER = new Set([
  'latency_mean',
  'latency_total',
  'llm_calls_per_question',
  'llm_calls',
  'prompt_tokens',
  'completion_tokens',
  'embedding_tokens',
  'cost_usd',
  'hallucination',
  'refusal',
  'context_chars_mean',
  'context_chars'
])

export function metricLabel(key: string): string {
  if (METRIC_LABELS[key]) return METRIC_LABELS[key]
  if (key.startsWith('latency_')) return `Latency · ${key.slice(8).replace(/_/g, ' ')}`
  return key.replace(/_/g, ' ')
}

export function fmtLatency(v: unknown): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '–'
  if (v < 0.01) return `${(v * 1000).toFixed(2)} ms`
  if (v < 1) return `${Math.round(v * 1000)} ms`
  return `${v.toFixed(2)} s`
}

export function fmtMetric(key: string, v: unknown): string {
  if (v === null || v === undefined) return '–'
  if (typeof v !== 'number' || Number.isNaN(v)) return String(v)
  if (key.startsWith('latency')) return fmtLatency(v)
  if (key.endsWith('_usd')) return v === 0 ? '$0' : `$${v.toFixed(4)}`
  if (key.endsWith('_tokens') || key.startsWith('context_chars') || key === 'llm_calls')
    return Math.round(v).toLocaleString()
  if (key === 'llm_calls_per_question') return v.toFixed(2)
  return v.toFixed(3)
}

/** Positive when `b` is better than `a` for this metric, negative when worse, 0 when equal/unknown. */
export function improvement(key: string, diff: number | undefined): number {
  if (typeof diff !== 'number' || diff === 0) return 0
  return LOWER_IS_BETTER.has(key) ? -Math.sign(diff) : Math.sign(diff)
}
