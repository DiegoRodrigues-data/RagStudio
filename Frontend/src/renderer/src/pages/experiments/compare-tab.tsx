import { useTechniqueTitle } from '@/hooks/use-technique-title'
import { useMemo } from 'react'
import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import { api } from '@/lib/api'
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
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { LoadingState } from '@/components/shared/loading-state'
import { fmtMetric, improvement, metricLabel } from '@/components/shared/metrics'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import type { PairedComparison, RunTableRow } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ByQuestion } from './compare-questions'
import type { ExpKey } from './i18n'

function runLabel(r: RunTableRow, technique: string): string {
  const params = r.params && r.params !== '{}' ? ` ${r.params}` : ''
  return `#${r.seq} ${technique} · ${r.retrieval_mode} · k=${r.k} · ${r.chunking}${params}`
}

function RunPicker({
  label,
  value,
  runs,
  onChange
}: {
  label: string
  value: string | null
  runs: RunTableRow[]
  onChange: (id: string) => void
}): React.JSX.Element {
  const title = useTechniqueTitle()
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1">
      <span className="text-xs font-medium">{label}</span>
      <Select value={value ?? ''} onValueChange={onChange}>
        <SelectTrigger className="w-full font-mono text-xs">
          <SelectValue placeholder="–" />
        </SelectTrigger>
        <SelectContent>
          {runs.map((r) => (
            <SelectItem key={r.run_id} value={r.run_id} className="font-mono text-xs">
              {runLabel(r, title(r.technique))}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function Paired({
  t,
  runs,
  runA,
  runB,
  onChange
}: {
  t: PageT<ExpKey>
  runs: RunTableRow[]
  runA: string | null
  runB: string | null
  onChange: (a: string | null, b: string | null) => void
}): React.JSX.Element {
  const loader = useMemo(
    () => (runA && runB ? () => api.compare.runs(runA, runB) : null),
    [runA, runB]
  )
  const cmp = useApiData<PairedComparison>(loader)
  const data = runA && runB ? cmp.data : null
  const diff = Object.entries(data?.config_diff ?? {})

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-3">
        <RunPicker
          label={t('compare.runA')}
          value={runA}
          runs={runs}
          onChange={(v) => onChange(v, runB)}
        />
        <RunPicker
          label={t('compare.runB')}
          value={runB}
          runs={runs}
          onChange={(v) => onChange(runA, v)}
        />
      </div>
      {!runA || !runB ? (
        <EmptyState title={t('compare.pick')} />
      ) : (
        <>
          <ErrorAlert title={t('common.errorTitle')} message={cmp.error} />
          {cmp.loading && !data && <LoadingState rows={6} />}
          {data && (
            <div className="grid items-start gap-4 xl:grid-cols-[20rem_minmax(0,1fr)]">
              <section className="rounded-lg border bg-card p-3">
                <h3 className="mb-2 text-sm font-semibold">{t('compare.diff')}</h3>
                {diff.length === 0 ? (
                  <p className="text-xs text-muted-foreground">{t('compare.same')}</p>
                ) : (
                  <dl className="flex flex-col gap-2 text-xs">
                    {diff.map(([key, v]) => (
                      <div key={key}>
                        <dt className="font-medium">{key}</dt>
                        <dd className="font-mono text-[11px] break-all text-muted-foreground">
                          A: {JSON.stringify(v.a)}
                          <br />
                          B: {JSON.stringify(v.b)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
                <p className="mt-3 text-xs text-muted-foreground">
                  {t('compare.common', { n: data.common_questions })}
                </p>
              </section>
              <section className="flex min-w-0 flex-col gap-2">
                <div className="overflow-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('compare.metric')}</TableHead>
                        <TableHead className="text-right">{t('compare.meanA')}</TableHead>
                        <TableHead className="text-right">{t('compare.meanB')}</TableHead>
                        <TableHead className="text-right">{t('compare.delta')}</TableHead>
                        <TableHead className="text-right">{t('compare.ci')}</TableHead>
                        <TableHead className="text-right">{t('compare.p')}</TableHead>
                        <TableHead className="text-right">{t('compare.dz')}</TableHead>
                        <TableHead className="text-right">{t('compare.n')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Object.entries(data.metrics).map(([name, s]) => {
                        const dir = improvement(name, s.mean_diff)
                        const Icon = dir > 0 ? ArrowUp : dir < 0 ? ArrowDown : Minus
                        return (
                          <TableRow key={name}>
                            <TableCell className="text-sm">{metricLabel(name)}</TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">
                              {fmtMetric(name, s.mean_a)}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">
                              {fmtMetric(name, s.mean_b)}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">
                              <span
                                className="inline-flex items-center gap-1"
                                title={
                                  dir > 0 ? t('compare.better') : dir < 0 ? t('compare.worse') : ''
                                }
                              >
                                <Icon
                                  className={cn(
                                    'size-3',
                                    dir > 0 && 'text-emerald-600 dark:text-emerald-400',
                                    dir < 0 && 'text-destructive',
                                    dir === 0 && 'text-muted-foreground'
                                  )}
                                />
                                {s.mean_diff === undefined
                                  ? '–'
                                  : `${s.mean_diff > 0 ? '+' : ''}${fmtMetric(name, s.mean_diff)}`}
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">
                              {s.ci95
                                ? `[${fmtMetric(name, s.ci95[0])}, ${fmtMetric(name, s.ci95[1])}]`
                                : '–'}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">
                              {s.permutation_p_holm?.toFixed(3) ?? '–'}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">
                              {typeof s.cohens_dz === 'number' ? s.cohens_dz.toFixed(2) : '–'}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">
                              {s.n}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
                <p className="text-xs text-muted-foreground">{t('compare.note')}</p>
              </section>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function CompareTab({
  t,
  runbookId,
  refreshKey,
  runA,
  runB,
  onChange,
  onOpenAnswer
}: {
  t: PageT<ExpKey>
  runbookId: string | null
  refreshKey: string
  runA: string | null
  runB: string | null
  onChange: (a: string | null, b: string | null) => void
  onOpenAnswer: (resultId: number) => void
}): React.JSX.Element {
  const loader = useMemo(
    () => (runbookId ? () => api.compare.table([runbookId]) : null),
    [runbookId]
  )
  const table = useApiData<{ rows: RunTableRow[] }>(loader, refreshKey)
  if (!runbookId) return <EmptyState title={t('results.noRunbook')} />
  const runs = table.data?.rows ?? []
  return (
    <Tabs defaultValue="questions" className="gap-3">
      <TabsList>
        <TabsTrigger value="questions">{t('compare.mode.questions')}</TabsTrigger>
        <TabsTrigger value="runs">{t('compare.mode.runs')}</TabsTrigger>
      </TabsList>
      <TabsContent value="questions">
        <ByQuestion
          t={t}
          runbookId={runbookId}
          refreshKey={refreshKey}
          onOpenAnswer={onOpenAnswer}
        />
      </TabsContent>
      <TabsContent value="runs">
        <Paired t={t} runs={runs} runA={runA} runB={runB} onChange={onChange} />
      </TabsContent>
    </Tabs>
  )
}
