import { TechniqueName } from '@/components/shared/technique-name'
import { useCallback, useMemo, useState } from 'react'
import { api } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Bar } from '@/components/shared/bar'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { FieldRow } from '@/components/shared/field-row'
import { LoadingState } from '@/components/shared/loading-state'
import {
  ALL_METRICS,
  BOUNDED,
  LOWER_IS_BETTER,
  fmtMetric,
  metricLabel
} from '@/components/shared/metrics'
import { PageHeader } from '@/components/shared/page-header'
import { RunbookPicker } from '@/components/shared/runbook-picker'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT, type PageT } from '@/components/shared/use-page-t'
import type { CharacteristicsAnalysis, Dict, GroupRow, RunbookSummary } from '@/lib/types'
import { dict, type AnKey } from './i18n'

const AXES = [
  'technique',
  'chunking',
  'retrieval_mode',
  'reranker',
  'k',
  'llm',
  'embedding_model',
  'enrich',
  'seed',
  'corpus'
]

function AxisView({ t, ids }: { t: PageT<AnKey>; ids: string[] }): React.JSX.Element {
  const [by, setBy] = useState('technique')
  const [metric, setMetric] = useState('recall')
  const groups = useApiData<{ groups: GroupRow[]; runs: number }>(
    useMemo(() => () => api.compare.group(ids, by), [ids, by])
  )
  const rows = useMemo(() => groups.data?.groups ?? [], [groups.data])
  const available = ALL_METRICS.filter((m) => rows.some((r) => typeof r[m] === 'number'))
  const shown = available.includes(metric) ? metric : (available[0] ?? metric)
  const lower = LOWER_IS_BETTER.has(shown)
  const sorted = [...rows]
    .filter((r) => typeof r[shown] === 'number')
    .sort((a, b) => ((b[shown] as number) - (a[shown] as number)) * (lower ? -1 : 1))
  const max = BOUNDED.has(shown) ? 1 : Math.max(0.000001, ...sorted.map((r) => r[shown] as number))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <FieldRow label={t('axis.by')}>
          <Select value={by} onValueChange={setBy}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {AXES.map((a) => (
                <SelectItem key={a} value={a}>
                  {a}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldRow>
        <FieldRow label={t('axis.metric')}>
          <Select value={shown} onValueChange={setMetric}>
            <SelectTrigger className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {available.map((m) => (
                <SelectItem key={m} value={m}>
                  {metricLabel(m)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldRow>
        <p className="max-w-xl text-xs text-muted-foreground">{t('axis.sameIndex')}</p>
      </div>
      <ErrorAlert title={t('errorTitle')} message={groups.error} />
      {groups.loading && !groups.data ? (
        <LoadingState rows={5} />
      ) : (
        <>
          <section className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold">
                {t('axis.chart', { metric: metricLabel(shown), axis: by })}
              </h3>
              <span className="text-xs text-muted-foreground">
                {lower ? t('axis.lower') : t('axis.higher')}
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {sorted.map((r) => (
                <Bar
                  key={String(r[by])}
                  label={String(r[by] ?? '–')}
                  value={r[shown] as number}
                  max={max}
                  text={fmtMetric(shown, r[shown])}
                  hint={
                    typeof r[`${shown}_stdev`] === 'number'
                      ? `${r.runs} ${t('axis.runs')} · ${t('axis.stdev')} ${fmtMetric(shown, r[`${shown}_stdev`])}`
                      : `${r.runs} ${t('axis.runs')}`
                  }
                />
              ))}
            </div>
          </section>
          <section className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold">{t('axis.table')}</h3>
            <div className="overflow-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{by}</TableHead>
                    <TableHead className="text-right">{t('axis.runs')}</TableHead>
                    {available.map((m) => (
                      <TableHead key={m} className="text-right whitespace-nowrap">
                        {metricLabel(m)}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow key={String(r[by])}>
                      <TableCell className="font-mono text-sm font-medium">
                        {String(r[by] ?? '–')}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">{r.runs}</TableCell>
                      {available.map((m) => (
                        <TableCell key={m} className="text-right font-mono text-xs tabular-nums">
                          {fmtMetric(m, r[m])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

const CHAR_METRICS = ['recall', 'mrr', 'f1', 'faithfulness', 'latency_total']

function MeansTable({
  title,
  rows,
  keyName
}: {
  title: string
  rows: Dict[]
  keyName: string
}): React.JSX.Element | null {
  if (rows.length === 0) return null
  const metrics = CHAR_METRICS.filter((m) => rows.some((r) => typeof r[m] === 'number'))
  return (
    <section className="flex min-w-0 flex-col gap-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>technique</TableHead>
              <TableHead>{keyName}</TableHead>
              <TableHead className="text-right">n</TableHead>
              {metrics.map((m) => (
                <TableHead key={m} className="text-right whitespace-nowrap">
                  {metricLabel(m)}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r, i) => (
              <TableRow key={i}>
                <TableCell className="text-xs font-medium">
                  <TechniqueName name={String(r.technique)} />
                </TableCell>
                <TableCell className="text-xs">{String(r[keyName] ?? '–')}</TableCell>
                <TableCell className="text-right font-mono text-xs">{String(r.n)}</TableCell>
                {metrics.map((m) => (
                  <TableCell key={m} className="text-right font-mono text-xs tabular-nums">
                    {fmtMetric(m, r[m])}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  )
}

function CharacteristicsView({ t, ids }: { t: PageT<AnKey>; ids: string[] }): React.JSX.Element {
  const analysis = useApiData<CharacteristicsAnalysis>(
    useMemo(() => () => api.compare.characteristics(ids), [ids])
  )
  const [filter, setFilter] = useState('')
  const d = analysis.data
  const needle = filter.trim().toLowerCase()
  const correlations = (d?.correlations ?? []).filter(
    (c) => !needle || `${c.technique} ${c.metric} ${c.feature}`.toLowerCase().includes(needle)
  )
  if (analysis.loading && !d) return <LoadingState rows={6} />
  return (
    <div className="flex flex-col gap-4">
      <ErrorAlert title={t('errorTitle')} message={analysis.error} />
      {d && (
        <>
          <div className="rounded-md border bg-muted/40 p-2.5 text-xs">
            <span className="font-medium">
              {t('char.summary', { rows: d.rows, docs: d.documents })}
            </span>{' '}
            ·{' '}
            {t('char.target', {
              gold: d.target_sources.gold ?? 0,
              top: d.target_sources.top_retrieved ?? 0
            })}{' '}
            <span className="text-muted-foreground">{t('char.caution')}</span>
          </div>
          <section className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">{t('char.correlations')}</h3>
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder={t('char.filter')}
                className="h-8 max-w-xs"
              />
            </div>
            {correlations.length === 0 ? (
              <EmptyState title={t('char.none')} />
            ) : (
              <div className="max-h-96 overflow-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('char.technique')}</TableHead>
                      <TableHead>{t('char.metric')}</TableHead>
                      <TableHead>{t('char.feature')}</TableHead>
                      <TableHead className="w-64">{t('char.spearman')}</TableHead>
                      <TableHead className="text-right">{t('char.n')}</TableHead>
                      <TableHead className="text-right">{t('char.docs')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {correlations.slice(0, 120).map((c, i) => (
                      <TableRow key={i}>
                        <TableCell className="text-xs font-medium">
                          <TechniqueName name={c.technique} />
                        </TableCell>
                        <TableCell className="text-xs">{metricLabel(c.metric)}</TableCell>
                        <TableCell className="font-mono text-xs">{c.feature}</TableCell>
                        <TableCell>
                          <Diverging value={c.spearman} />
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">{c.n}</TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {c.documents}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </section>
          <div className="grid items-start gap-4 xl:grid-cols-2">
            <MeansTable title={t('char.bins')} rows={d.size_bins} keyName="bin" />
            <MeansTable title={t('char.byLanguage')} rows={d.by_language} keyName="language" />
            <MeansTable title={t('char.byFormat')} rows={d.by_format} keyName="format" />
            <MeansTable title={t('char.byCorpus')} rows={d.by_corpus} keyName="corpus" />
          </div>
        </>
      )}
    </div>
  )
}

/** Correlation on a fixed -1..+1 scale: the bar grows from a neutral midpoint, the value is in ink. */
function Diverging({ value }: { value: number }): React.JSX.Element {
  const width = Math.min(50, Math.abs(value) * 50)
  return (
    <span className="flex items-center gap-2">
      <span className="relative h-3 flex-1 rounded-sm bg-muted">
        <span className="absolute inset-y-0 left-1/2 w-px bg-border" />
        <span
          className="absolute inset-y-0 bg-(--series-1)"
          style={
            value >= 0 ? { left: '50%', width: `${width}%` } : { right: '50%', width: `${width}%` }
          }
        />
      </span>
      <span className="w-12 text-right font-mono text-xs tabular-nums">
        {value > 0 ? '+' : ''}
        {value.toFixed(2)}
      </span>
    </span>
  )
}

export default function AnalysisPage(): React.JSX.Element {
  const t = usePageT(dict)
  const runbooks = useApiData<RunbookSummary[]>(useCallback(() => api.experiments.list(), []))
  const [picked, setPicked] = useState<string[] | null>(null)
  const lastUsable = (runbooks.data ?? []).filter((r) => r.completed > 0).at(-1)?.id ?? null
  const ids = useMemo(() => picked ?? (lastUsable ? [lastUsable] : []), [picked, lastUsable])

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <PageHeader />
      <ErrorAlert title={t('errorTitle')} message={runbooks.error} />
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[17rem_minmax(0,1fr)]">
        <div className="flex min-h-48 flex-col rounded-lg border bg-card lg:h-[calc(100svh-11.5rem)]">
          <div className="border-b px-3 py-2 text-sm font-medium">{t('pick.title')}</div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="p-2">
              <RunbookPicker
                runbooks={runbooks.data ?? []}
                value={ids}
                onChange={setPicked}
                emptyLabel={t('pick.empty')}
                runsLabel={(done, total) => t('pick.runs', { done, total })}
              />
            </div>
          </ScrollArea>
        </div>
        <div className="min-w-0">
          {ids.length === 0 ? (
            <EmptyState title={t('pick.hint')} />
          ) : (
            <Tabs defaultValue="axis" className="gap-4">
              <TabsList>
                <TabsTrigger value="axis">{t('tabs.axis')}</TabsTrigger>
                <TabsTrigger value="characteristics">{t('tabs.characteristics')}</TabsTrigger>
              </TabsList>
              <TabsContent value="axis">
                <AxisView t={t} ids={ids} />
              </TabsContent>
              <TabsContent value="characteristics">
                <CharacteristicsView t={t} ids={ids} />
              </TabsContent>
            </Tabs>
          )}
        </div>
      </div>
    </div>
  )
}
