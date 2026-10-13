import type { ChunkingConfig } from './types'

export function chunkingLabel(c: ChunkingConfig | undefined | null): string {
  if (!c) return '–'
  const parent = c.parent_size ? ` · parent ${c.parent_size}` : ''
  return `${c.strategy} ${c.size}/${c.overlap}${parent}`
}

/** Parse "3, 5,8" into numbers; null when any item is not a finite number. */
export function parseNumbers(text: string): number[] | null {
  const parts = text
    .split(/[,;\s]+/)
    .map((p) => p.trim())
    .filter(Boolean)
  const out = parts.map(Number)
  return out.every((n) => Number.isFinite(n)) ? out : null
}

export function parseList(text: string): string[] {
  return text
    .split(/[,;\n]+/)
    .map((p) => p.trim())
    .filter(Boolean)
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

/** `ragstudio://local/<path>`: served by the main process for files inside the project/data dirs. */
export function localUrl(path: string): string {
  return `ragstudio://local/${path.split('/').map(encodeURIComponent).join('/')}`
}
