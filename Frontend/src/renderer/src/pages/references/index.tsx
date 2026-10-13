import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { LoadingState } from '@/components/shared/loading-state'
import { PageHeader } from '@/components/shared/page-header'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT } from '@/components/shared/use-page-t'
import { useLanguage, useT } from '@/hooks/use-t'
import type { ReferenceCatalog, ReferenceEntry } from '@/lib/types'
import { cn } from '@/lib/utils'
import { EntryDetail } from './entry-detail'
import { dict, type RefKey } from './i18n'
import { groupEntries, searchEntries, sourceRows, type View } from './lookup'
import { SourcesView } from './sources-view'

const MONO_KINDS = new Set(['component'])

function ViewTabs({
  views,
  value,
  onChange
}: {
  views: { id: View; label: string; count: number }[]
  value: View
  onChange: (view: View) => void
}): React.JSX.Element {
  return (
    <div role="tablist" className="flex flex-wrap gap-1 rounded-lg bg-muted p-1">
      {views.map((v) => (
        <button
          key={v.id}
          type="button"
          role="tab"
          aria-selected={value === v.id}
          onClick={() => onChange(v.id)}
          className={cn(
            'inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
            value === v.id
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground',
            v.count === 0 && value !== v.id && 'opacity-50'
          )}
        >
          {v.label}
          <span className="font-mono text-[10px] tabular-nums opacity-70">{v.count}</span>
        </button>
      ))}
    </div>
  )
}

function EntryList({
  entries,
  catalog,
  selected,
  showKind,
  kindLabel,
  onSelect
}: {
  entries: ReferenceEntry[]
  catalog: ReferenceCatalog
  selected: string | undefined
  showKind: boolean
  kindLabel: (kind: string) => string
  onSelect: (id: string) => void
}): React.JSX.Element {
  return (
    <nav className="flex flex-col pb-2">
      {groupEntries(entries).map((group, i, all) => (
        <div key={`${group.kind}:${group.group}`}>
          {showKind && (i === 0 || all[i - 1].kind !== group.kind) && (
            <p className="sticky top-0 z-10 border-b bg-background px-3 py-1.5 text-xs font-semibold tracking-wide uppercase">
              {kindLabel(group.kind)}
            </p>
          )}
          <p className="px-3 pt-3 pb-1 text-[11px] font-medium text-muted-foreground">
            {catalog.groups[group.group] ?? group.group}
          </p>
          {group.entries.map((entry) => (
            <button
              key={entry.id}
              type="button"
              aria-current={selected === entry.id}
              onClick={() => onSelect(entry.id)}
              className={cn(
                'flex w-full flex-col gap-0.5 border-l-2 border-transparent px-3 py-1.5 text-left transition-colors outline-none hover:bg-accent/60 focus-visible:bg-accent/60',
                selected === entry.id && 'border-primary bg-accent'
              )}
            >
              <span
                className={cn(
                  'truncate text-sm font-medium',
                  MONO_KINDS.has(entry.kind) && 'font-mono text-[13px]'
                )}
              >
                {entry.name}
              </span>
              <span className="truncate text-xs text-muted-foreground">{entry.summary}</span>
            </button>
          ))}
        </div>
      ))}
    </nav>
  )
}

export default function ReferencesPage(): React.JSX.Element {
  const t = usePageT(dict)
  const gt = useT()
  const { language } = useLanguage()
  const lang = language === 'en' ? 'en' : 'pt'
  const loaded = useApiData<ReferenceCatalog>(useCallback(() => api.reference.list(lang), [lang]))
  const catalog = loaded.data
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState('')
  const view = (params.get('view') ?? 'all') as View
  const selectedId = params.get('id') ?? undefined

  const matched = useMemo(() => (catalog ? searchEntries(catalog, query) : []), [catalog, query])
  const sources = useMemo(() => (catalog ? sourceRows(catalog, query) : []), [catalog, query])
  const visible =
    view === 'all' || view === 'sources' ? matched : matched.filter((e) => e.kind === view)
  const selected = visible.find((e) => e.id === selectedId) ?? visible[0]

  const setView = (next: View): void => setParams(next === 'all' ? {} : { view: next })
  const select = (id: string): void => setParams(view === 'all' ? { id } : { view, id })
  /** Follow a cross-reference: leave the bibliography or a kind tab that does not hold the target. */
  const navigate = (id: string): void => {
    const target = catalog?.entries.find((e) => e.id === id)
    if (!target) return
    if (!matched.some((e) => e.id === id)) setQuery('')
    setParams(view === 'all' ? { id } : { view: target.kind, id })
  }

  const views = catalog
    ? [
        { id: 'all' as View, label: t('view.all'), count: matched.length },
        ...catalog.kinds.map((kind) => ({
          id: kind as View,
          label: t(`view.${kind}` as RefKey),
          count: matched.filter((e) => e.kind === kind).length
        })),
        { id: 'sources' as View, label: t('view.sources'), count: sources.length }
      ]
    : []

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <PageHeader />
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('search.placeholder')}
            className="h-9 pr-8 pl-8"
          />
          {query && (
            <Button
              variant="ghost"
              size="icon-xs"
              className="absolute top-1/2 right-1.5 -translate-y-1/2"
              aria-label={t('search.clear')}
              onClick={() => setQuery('')}
            >
              <X />
            </Button>
          )}
        </div>
        {catalog && <ViewTabs views={views} value={view} onChange={setView} />}
      </div>
      <ErrorAlert
        title={t('errorTitle')}
        message={loaded.error}
        retryLabel={gt('common.retry')}
        onRetry={loaded.reload}
      />
      {!catalog && loaded.loading && <LoadingState />}
      {catalog && view === 'sources' && <SourcesView rows={sources} t={t} onNavigate={navigate} />}
      {catalog && view !== 'sources' && visible.length === 0 && (
        <EmptyState icon={Search} title={t('empty.title')} description={t('empty.description')} />
      )}
      {catalog && view !== 'sources' && selected && (
        <div className="grid min-h-0 flex-1 grid-cols-[19rem_minmax(0,1fr)] overflow-hidden rounded-lg border xl:grid-cols-[22rem_minmax(0,1fr)]">
          <div className="flex min-h-0 flex-col border-r">
            <div className="min-h-0 flex-1 overflow-y-auto">
              <EntryList
                entries={visible}
                catalog={catalog}
                selected={selected.id}
                showKind={view === 'all'}
                kindLabel={(kind) => t(`view.${kind}` as RefKey)}
                onSelect={select}
              />
            </div>
            <p className="border-t px-3 py-1.5 text-xs text-muted-foreground">
              {t('list.count', { n: visible.length })}
            </p>
          </div>
          <div key={selected.id} className="min-h-0 overflow-y-auto p-6">
            <EntryDetail entry={selected} catalog={catalog} t={t} onNavigate={navigate} />
          </div>
        </div>
      )}
    </div>
  )
}
