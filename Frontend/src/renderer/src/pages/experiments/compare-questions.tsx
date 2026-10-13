import { useTechniqueTitle } from '@/hooks/use-technique-title'
import { TechniqueName } from '@/components/shared/technique-name'
import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Search, TriangleAlert, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { SortHeader, type SortState } from '@/components/shared/exp-sort-header'
import { sortRows } from '@/components/shared/exp-sort'
import { LoadingState } from '@/components/shared/loading-state'
import { fmtLatency, fmtMetric, metricLabel } from '@/components/shared/metrics'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import type { AnswerCell, QuestionAnswers } from '@/lib/types'
import { cn } from '@/lib/utils'
import type { ExpKey } from './i18n'

const ALL = '__all'
const PAGE = 50
const GROUP_PAGE = 30
const MAX_PINNED = 4
const FACETS = ['technique', 'retrieval_mode', 'reranker', 'k', 'chunking'] as const
type Facet = (typeof FACETS)[number]
const QUALITY = [
  'recall',
  'mrr',
  'context_coverage',
  'f1',
  'accuracy',
  'faithfulness',
  'hallucination'
] as const
type GroupMode = 'none' | 'technique' | 'answer'

const FACET_LABEL: Record<Facet, ExpKey> = {
  technique: 'compare.q.f.technique',
  retrieval_mode: 'compare.q.f.mode',
  reranker: 'compare.q.f.reranker',
  k: 'compare.q.f.k',
  chunking: 'compare.q.f.chunking'
}

function normalized(answer: string): string {
  return answer.trim().replace(/\s+/g, ' ').toLowerCase()
}

function mean(values: number[]): number | null {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null
}

function distinctAnswers(cells: AnswerCell[]): number {
  return new Set(cells.map((c) => normalized(c.error ?? c.answer))).size
}

function configLine(c: AnswerCell): string {
  const reranker = c.reranker !== 'none' ? ` · ${c.reranker}` : ''
  const params = c.params !== '{}' ? ` · ${c.params}` : ''
  return `${c.retrieval_mode}${reranker} · k=${c.k} · ${c.chunking}${params}`
}

function RunsTable({
  t,
  cells,
  columns,
  metrics,
  sort,
  onSort,
  pinned,
  onPin,
  onOpen
}: {
  t: PageT<ExpKey>
  cells: AnswerCell[]
  /** Configuration columns worth showing (the ones that vary in this question). */
  columns: Facet[]
  metrics: readonly (typeof QUALITY)[number][]
  sort: SortState | null
  onSort: (next: SortState) => void
  pinned: number[]
  onPin: (resultId: number) => void
  onOpen: (resultId: number) => void
}): React.JSX.Element {
  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <SortHeader colKey="technique" sort={sort} onSort={onSort}>
              {t('compare.q.col.config')}
            </SortHeader>
            <TableHead className="w-full min-w-64">{t('compare.q.col.answer')}</TableHead>
            {metrics.map((m) => (
              <SortHeader key={m} colKey={m} sort={sort} onSort={onSort} numeric>
                {metricLabel(m)}
              </SortHeader>
            ))}
            <SortHeader colKey="latency_total" sort={sort} onSort={onSort} numeric>
              {t('compare.q.col.latency')}
            </SortHeader>
            <SortHeader colKey="llm_calls" sort={sort} onSort={onSort} numeric>
              {t('compare.q.col.calls')}
            </SortHeader>
            <SortHeader colKey="context_chars" sort={sort} onSort={onSort} numeric>
              {t('compare.q.col.context')}
            </SortHeader>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cells.map((c) => {
            const isPinned = pinned.includes(c.result_id)
            return (
              <TableRow
                key={c.result_id}
                className={cn('cursor-pointer align-top', isPinned && 'bg-muted/60')}
                onClick={() => onOpen(c.result_id)}
              >
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={isPinned}
                    disabled={!isPinned && pinned.length >= MAX_PINNED}
                    onCheckedChange={() => onPin(c.result_id)}
                    aria-label={t('compare.q.pin')}
                  />
                </TableCell>
                <TableCell className="whitespace-nowrap">
                  {columns.includes('technique') && (
                    <TechniqueName name={c.technique} className="block text-sm font-medium" />
                  )}
                  <div className="font-mono text-[11px] text-muted-foreground">
                    {[
                      `#${c.seq}`,
                      ...columns
                        .filter((col) => col !== 'technique')
                        .map((col) => (col === 'k' ? `k=${c.k}` : String(c[col])))
                    ].join(' · ')}
                  </div>
                </TableCell>
                <TableCell className="whitespace-normal">
                  <p
                    className={cn(
                      'line-clamp-3 text-xs leading-relaxed',
                      c.error && 'text-destructive'
                    )}
                  >
                    {c.error ?? c.answer}
                  </p>
                  {c.warnings.length > 0 && (
                    <p
                      className="mt-1 flex items-start gap-1 text-[11px] text-amber-700 dark:text-amber-400"
                      title={c.warnings.join('\n')}
                    >
                      <TriangleAlert className="mt-px size-3 shrink-0" />
                      <span className="line-clamp-1">{c.warnings.join(' · ')}</span>
                    </p>
                  )}
                </TableCell>
                {metrics.map((m) => (
                  <TableCell key={m} className="text-right font-mono text-xs tabular-nums">
                    {fmtMetric(m, c[m])}
                  </TableCell>
                ))}
                <TableCell className="text-right font-mono text-xs whitespace-nowrap tabular-nums">
                  {fmtLatency(c.latency_total)}
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {c.llm_calls}
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {c.context_chars.toLocaleString()}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

function PinnedCard({
  t,
  cell,
  metrics,
  onOpen,
  onRemove
}: {
  t: PageT<ExpKey>
  cell: AnswerCell
  metrics: readonly (typeof QUALITY)[number][]
  onOpen: () => void
  onRemove: () => void
}): React.JSX.Element {
  return (
    <article className="flex min-w-0 flex-col gap-2 rounded-lg border bg-card p-3">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">
            <span className="font-mono">#{cell.seq}</span> <TechniqueName name={cell.technique} />
          </div>
          <div
            className="truncate font-mono text-[11px] text-muted-foreground"
            title={configLine(cell)}
          >
            {configLine(cell)}
          </div>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button variant="outline" size="xs" onClick={onOpen}>
            {t('compare.q.open')}
          </Button>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={onRemove}
            aria-label={t('compare.q.unpin')}
          >
            <X />
          </Button>
        </div>
      </header>
      <p
        className={cn(
          'max-h-72 overflow-y-auto rounded-md bg-muted/50 p-2 text-xs leading-relaxed whitespace-pre-wrap',
          cell.error && 'text-destructive'
        )}
      >
        {cell.error ?? cell.answer}
      </p>
      <div className="flex flex-wrap gap-1">
        {metrics
          .filter((m) => cell[m] !== null)
          .map((m) => (
            <Badge key={m} variant="secondary" className="font-mono">
              {metricLabel(m)} {fmtMetric(m, cell[m])}
            </Badge>
          ))}
        <Badge variant="outline" className="font-mono">
          {fmtLatency(cell.latency_total)}
        </Badge>
        <Badge variant="outline" className="font-mono">
          {t('compare.q.calls', { n: cell.llm_calls })}
        </Badge>
        <Badge variant="outline" className="font-mono">
          {cell.context_chars.toLocaleString()} ch
        </Badge>
      </div>
    </article>
  )
}

interface Group {
  key: string
  title: string
  cells: AnswerCell[]
}

function GroupRow({
  t,
  mode,
  group,
  open,
  onToggle,
  children
}: {
  t: PageT<ExpKey>
  mode: GroupMode
  group: Group
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}): React.JSX.Element {
  const Chevron = open ? ChevronDown : ChevronRight
  const latency = mean(group.cells.map((c) => c.latency_total))
  const calls = mean(group.cells.map((c) => c.llm_calls))
  const context = mean(group.cells.map((c) => c.context_chars))
  const techniques = useMemo(() => {
    const counts = new Map<string, number>()
    for (const c of group.cells) counts.set(c.technique, (counts.get(c.technique) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [group.cells])
  const failed = group.cells.every((c) => c.error)
  return (
    <li className="rounded-lg border bg-card">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-start gap-2 rounded-lg p-3 text-left outline-none hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring/50"
      >
        <Chevron className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          {mode === 'technique' ? (
            <span className="font-mono text-sm font-medium">{group.title}</span>
          ) : (
            <p
              className={cn(
                'text-xs leading-relaxed whitespace-pre-wrap',
                !open && 'line-clamp-2',
                failed && 'text-destructive'
              )}
            >
              {group.title}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-1">
            {mode === 'technique' ? (
              <Badge variant="secondary">
                {t('compare.q.distinct', { n: distinctAnswers(group.cells) })}
              </Badge>
            ) : (
              <>
                {techniques.slice(0, 8).map(([name, n]) => (
                  <Badge key={name} variant="secondary" className="font-mono">
                    {name}
                    {n > 1 && ` ×${n}`}
                  </Badge>
                ))}
                {techniques.length > 8 && <Badge variant="outline">+{techniques.length - 8}</Badge>}
              </>
            )}
          </div>
        </div>
        <dl className="grid shrink-0 grid-cols-4 gap-x-4 text-right font-mono text-xs tabular-nums">
          {(
            [
              [t('compare.q.col.runs'), String(group.cells.length)],
              [t('compare.q.col.latency'), fmtLatency(latency)],
              [t('compare.q.col.calls'), calls === null ? '–' : calls.toFixed(1)],
              [
                t('compare.q.col.context'),
                context === null ? '–' : Math.round(context).toLocaleString()
              ]
            ] as const
          ).map(([label, value]) => (
            <div key={label} className="flex w-20 flex-col">
              <dt className="truncate font-sans text-[11px] text-muted-foreground">{label}</dt>
              <dd className="font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      </button>
      {open && <div className="border-t p-2">{children}</div>}
    </li>
  )
}

export function ByQuestion({
  t,
  runbookId,
  refreshKey,
  onOpenAnswer
}: {
  t: PageT<ExpKey>
  runbookId: string
  refreshKey: string
  onOpenAnswer: (resultId: number) => void
}): React.JSX.Element {
  const answers = useApiData<QuestionAnswers[]>(
    useMemo(() => () => api.compare.answers([runbookId]), [runbookId]),
    refreshKey
  )
  const techTitle = useTechniqueTitle()
  const [picked, setPicked] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [facets, setFacets] = useState<Partial<Record<Facet, string>>>({})
  const [group, setGroup] = useState<GroupMode>('none')
  const [sort, setSort] = useState<SortState | null>({ key: 'seq', dir: 'asc' })
  const [pinned, setPinned] = useState<number[]>([])
  const [limit, setLimit] = useState(PAGE)
  const [openGroups, setOpenGroups] = useState<string[]>([])

  const questions = useMemo(() => answers.data ?? [], [answers.data])
  const current = questions.find((q) => q.question_id === picked) ?? questions[0] ?? null
  const all = useMemo(() => current?.answers ?? [], [current])

  const facetValues = useMemo(() => {
    const out = {} as Record<Facet, string[]>
    for (const f of FACETS) {
      const values = [...new Set(all.map((c) => String(c[f])))]
      out[f] = f === 'k' ? values.sort((a, b) => Number(a) - Number(b)) : values.sort()
    }
    return out
  }, [all])
  const columns = FACETS.filter((f) => facetValues[f].length > 1)
  const metrics = QUALITY.filter((m) => all.some((c) => c[m] !== null))

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    const rows = all.filter(
      (c) =>
        FACETS.every((f) => !facets[f] || String(c[f]) === facets[f]) &&
        (!needle ||
          `${c.technique} ${techTitle(c.technique)} ${c.error ?? c.answer} ${c.params}`
            .toLowerCase()
            .includes(needle))
    )
    return sortRows(rows, sort, (row, key) => row[key as keyof AnswerCell])
  }, [all, facets, search, sort, techTitle])

  const groups = useMemo<Group[]>(() => {
    if (group === 'none') return []
    const map = new Map<string, Group>()
    for (const c of filtered) {
      const text = c.error ?? c.answer
      const key = group === 'technique' ? c.technique : normalized(text)
      const entry = map.get(key) ?? {
        key,
        title: group === 'technique' ? techTitle(c.technique) : text,
        cells: []
      }
      entry.cells.push(c)
      map.set(key, entry)
    }
    const list = [...map.values()]
    return group === 'technique'
      ? list.sort((a, b) => a.title.localeCompare(b.title))
      : list.sort((a, b) => b.cells.length - a.cells.length)
  }, [filtered, group, techTitle])

  const resetPaging = (): void => {
    setLimit(PAGE)
    setOpenGroups([])
  }
  const active = search.trim() !== '' || FACETS.some((f) => facets[f])
  const togglePin = (id: number): void =>
    setPinned((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id].slice(0, MAX_PINNED)))
  const pinnedCells = pinned
    .map((id) => all.find((c) => c.result_id === id))
    .filter((c): c is AnswerCell => Boolean(c))

  if (answers.loading && !answers.data) return <LoadingState rows={6} />
  if (!current)
    return (
      <>
        <ErrorAlert title={t('common.errorTitle')} message={answers.error} />
        <EmptyState title={t('results.empty')} />
      </>
    )

  const total = group === 'none' ? filtered.length : groups.length
  const pageSize = group === 'none' ? PAGE : GROUP_PAGE
  const table = (cells: AnswerCell[], cols: Facet[]): React.JSX.Element => (
    <RunsTable
      t={t}
      cells={cells}
      columns={cols}
      metrics={metrics}
      sort={sort}
      onSort={setSort}
      pinned={pinned}
      onPin={togglePin}
      onOpen={onOpenAnswer}
    />
  )

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <section className="flex flex-col gap-2 rounded-lg border bg-card p-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          {questions.length > 1 ? (
            <Select
              value={current.question_id}
              onValueChange={(v) => {
                setPicked(v)
                setPinned([])
                setFacets({})
                resetPaging()
              }}
            >
              <SelectTrigger className="h-auto min-h-9 w-full max-w-3xl text-left whitespace-normal">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="max-w-3xl">
                {questions.map((q) => (
                  <SelectItem key={q.question_id} value={q.question_id}>
                    <span className="font-mono text-xs font-medium">{q.code}</span> · {q.text}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <h3 className="min-w-0 text-sm font-semibold">
              <span className="font-mono">{current.code}</span> · {current.text}
            </h3>
          )}
          <div className="flex shrink-0 gap-1.5">
            {questions.length > 1 && (
              <Badge variant="outline">{t('compare.q.questions', { n: questions.length })}</Badge>
            )}
            <Badge variant="secondary">{t('compare.q.runs', { n: all.length })}</Badge>
            <Badge variant="secondary">
              {t('compare.q.distinct', { n: distinctAnswers(all) })}
            </Badge>
          </div>
        </div>
        <div className="grid gap-x-6 gap-y-2 text-xs md:grid-cols-2">
          <div>
            <div className="text-muted-foreground">{t('answer.expected')}</div>
            <p className="whitespace-pre-wrap">
              {current.expected_answer || t('answer.noExpected')}
            </p>
          </div>
          <div>
            <div className="text-muted-foreground">{t('answer.gold')}</div>
            {current.gold_passages.length === 0 ? (
              <p>{t('compare.q.noGold')}</p>
            ) : (
              current.gold_passages.map((g, i) => (
                <p key={i} className="line-clamp-3" title={g.text}>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {g.document_id}
                  </span>{' '}
                  {g.text}
                </p>
              ))
            )}
          </div>
        </div>
        {metrics.length === 0 && (
          <p className="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-400">
            <TriangleAlert className="mt-px size-3.5 shrink-0" />
            {t('compare.q.noQuality')}
          </p>
        )}
      </section>

      {pinnedCells.length > 0 && (
        <section className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">
              {t('compare.q.pinned')}
              <span className="ml-2 font-normal text-muted-foreground">
                {pinnedCells.length}/{MAX_PINNED}
              </span>
            </h3>
            <Button variant="ghost" size="xs" onClick={() => setPinned([])}>
              {t('compare.q.unpinAll')}
            </Button>
          </div>
          <div
            className={cn(
              'grid items-start gap-3',
              pinnedCells.length === 2 && 'md:grid-cols-2',
              pinnedCells.length === 3 && 'md:grid-cols-3',
              pinnedCells.length >= 4 && 'md:grid-cols-2 2xl:grid-cols-4'
            )}
          >
            {pinnedCells.map((cell) => (
              <PinnedCard
                key={cell.result_id}
                t={t}
                cell={cell}
                metrics={metrics}
                onOpen={() => onOpenAnswer(cell.result_id)}
                onRemove={() => togglePin(cell.result_id)}
              />
            ))}
          </div>
        </section>
      )}

      <section className="flex flex-wrap items-end gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              resetPaging()
            }}
            placeholder={t('compare.q.search')}
            className="h-8 w-64 pl-7"
          />
        </div>
        {columns.map((f) => (
          <Select
            key={f}
            value={facets[f] ?? ALL}
            onValueChange={(v) => {
              setFacets((prev) => ({ ...prev, [f]: v === ALL ? undefined : v }))
              resetPaging()
            }}
          >
            <SelectTrigger size="sm" className={cn('min-w-32', facets[f] && 'border-primary')}>
              <span className="text-muted-foreground">{t(FACET_LABEL[f])}:</span>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t('compare.q.any')}</SelectItem>
              {facetValues[f].map((v) => (
                <SelectItem
                  key={v}
                  value={v}
                  className={f === 'k' || f === 'technique' ? '' : 'font-mono text-xs'}
                >
                  {f === 'technique' ? techTitle(v) : v}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ))}
        {active && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch('')
              setFacets({})
              resetPaging()
            }}
          >
            <X />
            {t('compare.q.clear')}
          </Button>
        )}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-muted-foreground tabular-nums">
            {t('compare.q.shown', { n: filtered.length, total: all.length })}
          </span>
          <Select
            value={group}
            onValueChange={(v) => {
              setGroup(v as GroupMode)
              resetPaging()
            }}
          >
            <SelectTrigger size="sm" className="min-w-44">
              <span className="text-muted-foreground">{t('compare.q.group')}:</span>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t('compare.q.group.none')}</SelectItem>
              <SelectItem value="technique">{t('compare.q.group.technique')}</SelectItem>
              <SelectItem value="answer">{t('compare.q.group.answer')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      {pinnedCells.length === 0 && filtered.length > 0 && (
        <p className="text-xs text-muted-foreground">{t('compare.q.pinHint')}</p>
      )}

      {filtered.length === 0 ? (
        <EmptyState title={t('compare.q.noMatch')} />
      ) : group === 'none' ? (
        table(filtered.slice(0, limit), columns)
      ) : (
        <ul className="flex flex-col gap-2">
          {groups.slice(0, limit).map((g) => {
            const open = openGroups.includes(g.key)
            return (
              <GroupRow
                key={g.key}
                t={t}
                mode={group}
                group={g}
                open={open}
                onToggle={() =>
                  setOpenGroups((prev) =>
                    open ? prev.filter((k) => k !== g.key) : [...prev, g.key]
                  )
                }
              >
                {table(
                  g.cells,
                  columns.filter((c) => !(group === 'technique' && c === 'technique'))
                )}
              </GroupRow>
            )
          })}
        </ul>
      )}

      {total > limit && (
        <Button
          variant="outline"
          size="sm"
          className="self-center"
          onClick={() => setLimit((n) => n + pageSize)}
        >
          {t('compare.q.more', { n: Math.min(pageSize, total - limit), rest: total - limit })}
        </Button>
      )}
    </div>
  )
}
