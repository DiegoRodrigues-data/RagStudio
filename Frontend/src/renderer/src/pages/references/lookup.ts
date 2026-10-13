import type { ReferenceCatalog, ReferenceEntry, ReferenceKind, ReferenceSource } from '@/lib/types'

export type View = 'all' | ReferenceKind | 'sources'

/** Lower-case and accent-free, so "metrica" finds "métrica". */
export function fold(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

export function sourceLabel(source: ReferenceSource): string {
  const who = source.authors || source.venue || source.title
  return source.year ? `${who} (${source.year})` : who
}

function haystack(entry: ReferenceEntry, catalog: ReferenceCatalog): string {
  return fold(
    [
      entry.name,
      entry.id,
      entry.facts.identifier ?? '',
      entry.summary,
      catalog.groups[entry.group] ?? '',
      ...(entry.facts.keys ?? []),
      ...entry.sections.map((s) => s.text)
    ].join(' ')
  )
}

/** Entries matching every word of the query, in catalog order. */
export function searchEntries(catalog: ReferenceCatalog, query: string): ReferenceEntry[] {
  const words = fold(query).split(/\s+/).filter(Boolean)
  if (words.length === 0) return catalog.entries
  return catalog.entries.filter((entry) => {
    const text = haystack(entry, catalog)
    return words.every((w) => text.includes(w))
  })
}

export interface EntryGroup {
  kind: ReferenceKind
  group: string
  entries: ReferenceEntry[]
}

/** Consecutive runs of the same kind + group, preserving catalog order. */
export function groupEntries(entries: ReferenceEntry[]): EntryGroup[] {
  const out: EntryGroup[] = []
  for (const entry of entries) {
    const last = out[out.length - 1]
    if (last && last.kind === entry.kind && last.group === entry.group) last.entries.push(entry)
    else out.push({ kind: entry.kind, group: entry.group, entries: [entry] })
  }
  return out
}

export interface SourceRow {
  key: string
  source: ReferenceSource
  usedBy: ReferenceEntry[]
}

export function sourceRows(catalog: ReferenceCatalog, query: string): SourceRow[] {
  const words = fold(query).split(/\s+/).filter(Boolean)
  return Object.entries(catalog.sources)
    .map(([key, source]) => ({
      key,
      source,
      usedBy: catalog.entries.filter((e) => e.sources.includes(key))
    }))
    .filter(({ source, usedBy }) => {
      const text = fold(
        `${source.authors} ${source.title} ${source.venue} ${source.year ?? ''} ${usedBy.map((e) => e.name).join(' ')}`
      )
      return words.every((w) => text.includes(w))
    })
    .sort((a, b) => sourceLabel(a.source).localeCompare(sourceLabel(b.source)))
}
