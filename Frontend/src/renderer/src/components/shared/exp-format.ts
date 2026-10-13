/** Number / id / date formatting shared by the Experiments and Evidence pages. */

export function fmtScore(v: unknown, digits = 3): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '–'
  return v.toFixed(digits)
}

export function fmtMs(v: unknown): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '–'
  return `${Math.round(v)} ms`
}

export function fmtUsd(v: unknown): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '–'
  return `$${v.toFixed(4)}`
}

export function fmtInt(v: unknown): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '–'
  return Math.round(v).toLocaleString()
}

export function fmtPct(v: unknown, digits = 1): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '–'
  return `${(v * 100).toFixed(digits)}%`
}

export function fmtSeconds(v: unknown): string {
  if (typeof v !== 'number' || Number.isNaN(v) || v < 0) return '–'
  const s = Math.round(v)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

export function fmtDate(iso: unknown, locale?: string): string {
  if (typeof iso !== 'string' || !iso) return '–'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' })
}

/** `rb_20261011_145226_920e0f_run_0003` → `run_0003`; otherwise the first `n` characters. */
export function shortId(id: unknown, n = 12): string {
  if (typeof id !== 'string') return '–'
  const m = /_(run_\d+(?:_rep\d+)?)$/.exec(id)
  if (m) return m[1]
  return id.length > n ? `${id.slice(0, n)}…` : id
}

export function shortHash(h: unknown, n = 12): string {
  if (typeof h !== 'string' || !h) return '–'
  return h.length > n ? `${h.slice(0, n)}…` : h
}

/** Metrics where a lower value is better (latency, cost, error rates). */
export const LOWER_IS_BETTER = new Set([
  'avg_latency_ms',
  'avg_retrieval_latency_ms',
  'avg_inference_latency_ms',
  'total_cost_usd',
  'hallucination_rate',
  'refusal_rate',
  'failure_rate',
  'total_retries',
  'total_input_tokens',
  'total_output_tokens',
  'latency_ms'
])

/** Pick the right formatter for a metric key. */
export function fmtMetric(key: string, v: unknown): string {
  if (typeof v === 'boolean') return v ? 'yes' : 'no'
  if (typeof v !== 'number') return v == null ? '–' : String(v)
  if (key.endsWith('_ms')) return fmtMs(v)
  if (key.endsWith('_usd')) return fmtUsd(v)
  // counts are integers: tokens, retrieved chunks, retries, totals
  if (
    key.startsWith('total_') ||
    key.startsWith('num_') ||
    key.startsWith('n_') ||
    key === 'n' ||
    key.endsWith('_tokens') ||
    key.endsWith('_count')
  )
    return fmtInt(v)
  return fmtScore(v)
}
