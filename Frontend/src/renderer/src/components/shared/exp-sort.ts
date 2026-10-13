export interface SortState {
  key: string
  dir: 'asc' | 'desc'
}

/** Generic comparator: numbers before strings, null/undefined last. */
export function compareValues(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0
  if (a == null) return 1
  if (b == null) return -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  if (typeof a === 'boolean' && typeof b === 'boolean') return Number(a) - Number(b)
  return String(a).localeCompare(String(b))
}

export function sortRows<T>(
  rows: T[],
  sort: SortState | null,
  pick: (row: T, key: string) => unknown
): T[] {
  if (!sort) return rows
  const sign = sort.dir === 'asc' ? 1 : -1
  return [...rows].sort((x, y) => sign * compareValues(pick(x, sort.key), pick(y, sort.key)))
}
