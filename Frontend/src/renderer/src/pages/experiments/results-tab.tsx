import { TechniqueName } from '@/components/shared/technique-name'
import { useMemo, useState } from 'react'
import { GitCompareArrows } from 'lucide-react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Switch } from '@/components/ui/switch'
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
import { StatusBadge } from '@/components/shared/exp-status-badge'
import { LoadingState } from '@/components/shared/loading-state'
import { ALL_METRICS, HEADLINE_METRICS, fmtMetric, metricLabel } from '@/components/shared/metrics'
import { MockBadge } from '@/components/shared/mock-notice'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import { useStatusLabel } from '@/components/shared/use-status-label'
import type { RunTableRow, RunbookStatus } from '@/lib/types'
import type { ExpKey } from './i18n'

export function ResultsTab({
  t,
  runbookId,
  refreshKey,
  onOpenRun,
  onCompare
}: {
  t: PageT<ExpKey>
  runbookId: string | null
  refreshKey: string
  onOpenRun: (runId: string, seq: number) => void
  onCompare: (runA: string, runB: string) => void
}): React.JSX.Element {
  const statusLabel = useStatusLabel()
  const tableLoader = useMemo(
    () => (runbookId ? () => api.compare.table([runbookId]) : null),
    [runbookId]
  )
  const statusLoader = useMemo(
    () => (runbookId ? () => api.experiments.status(runbookId) : null),
    [runbookId]
  )
  const table = useApiData<{ rows: RunTableRow[] }>(tableLoader, refreshKey)
  const status = useApiData<RunbookStatus>(statusLoader, refreshKey)
  const [sort, setSort] = useState<SortState | null>({ key: 'seq', dir: 'asc' })
  const [allMetrics, setAllMetrics] = useState(false)
  const [picked, setPicked] = useState<string[]>([])

  const rows = useMemo(() => (runbookId ? (table.data?.rows ?? []) : []), [runbookId, table.data])
  const sorted = useMemo(() => sortRows(rows, sort, (r, key) => r[key]), [rows, sort])
  const metricCols = (allMetrics ? ALL_METRICS : HEADLINE_METRICS).filter((m) =>
    rows.some((r) => r[m] !== null && r[m] !== undefined)
  )
  const varying = (key: keyof RunTableRow): boolean => new Set(rows.map((r) => r[key])).size > 1
  const pending = (status.data?.runs ?? []).filter((r) => r.status !== 'completed')
  const replicaOf = new Map((status.data?.runs ?? []).map((r) => [r.id, r.replicates_run_id]))

  const toggle = (id: string): void =>
    setPicked((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(-2)
    )

  if (!runbookId) return <EmptyState title={t('results.noRunbook')} />

  return (
    <div className="flex flex-col gap-3">
      <ErrorAlert title={t('common.errorTitle')} message={table.error ?? status.error} />
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-xs">
          <Switch checked={allMetrics} onCheckedChange={setAllMetrics} />
          {t('results.allMetrics')}
        </label>
        <Button
          size="sm"
          variant="outline"
          disabled={picked.length !== 2}
          title={t('results.compareHint')}
          onClick={() => onCompare(picked[0], picked[1])}
        >
          <GitCompareArrows /> {t('results.compare')}
          {picked.length > 0 && <Badge variant="secondary">{picked.length}/2</Badge>}
        </Button>
        <MockBadge provider={rows[0]?.provider} />
      </div>

      {table.loading && !table.data ? (
        <LoadingState rows={6} />
      ) : rows.length === 0 ? (
        <EmptyState title={t('results.empty')} />
      ) : (
        <div className="overflow-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <SortHeader colKey="seq" sort={sort} onSort={setSort}>
                  {t('results.col.run')}
                </SortHeader>
                <SortHeader colKey="technique" sort={sort} onSort={setSort}>
                  {t('results.col.technique')}
                </SortHeader>
                {varying('retrieval_mode') && (
                  <SortHeader colKey="retrieval_mode" sort={sort} onSort={setSort}>
                    {t('results.col.mode')}
                  </SortHeader>
                )}
                {varying('reranker') && (
                  <SortHeader colKey="reranker" sort={sort} onSort={setSort}>
                    {t('results.col.reranker')}
                  </SortHeader>
                )}
                {varying('k') && (
                  <SortHeader colKey="k" sort={sort} onSort={setSort} numeric>
                    k
                  </SortHeader>
                )}
                {varying('chunking') && (
                  <SortHeader colKey="chunking" sort={sort} onSort={setSort}>
                    {t('results.col.chunking')}
                  </SortHeader>
                )}
                {varying('params') && <TableHead>{t('results.col.params')}</TableHead>}
                {varying('seed') && (
                  <SortHeader colKey="seed" sort={sort} onSort={setSort} numeric>
                    seed
                  </SortHeader>
                )}
                {metricCols.map((m) => (
                  <SortHeader key={m} colKey={m} sort={sort} onSort={setSort} numeric>
                    {metricLabel(m)}
                  </SortHeader>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((r) => (
                <TableRow
                  key={r.run_id}
                  className="cursor-pointer"
                  data-state={picked.includes(r.run_id) ? 'selected' : undefined}
                  onClick={() => onOpenRun(r.run_id, r.seq)}
                >
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={picked.includes(r.run_id)}
                      onCheckedChange={() => toggle(r.run_id)}
                      aria-label="select run"
                    />
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    #{r.seq}
                    {replicaOf.get(r.run_id) && (
                      <Badge variant="outline" className="ml-1.5">
                        {t('results.replica')}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm font-medium">
                    <TechniqueName name={r.technique} />
                  </TableCell>
                  {varying('retrieval_mode') && (
                    <TableCell className="text-xs">{r.retrieval_mode}</TableCell>
                  )}
                  {varying('reranker') && <TableCell className="text-xs">{r.reranker}</TableCell>}
                  {varying('k') && (
                    <TableCell className="text-right font-mono text-xs">{r.k}</TableCell>
                  )}
                  {varying('chunking') && (
                    <TableCell className="font-mono text-xs">{r.chunking}</TableCell>
                  )}
                  {varying('params') && (
                    <TableCell className="max-w-56 truncate font-mono text-[11px]" title={r.params}>
                      {r.params === '{}' ? '–' : r.params}
                    </TableCell>
                  )}
                  {varying('seed') && (
                    <TableCell className="text-right font-mono text-xs">{r.seed}</TableCell>
                  )}
                  {metricCols.map((m) => (
                    <TableCell
                      key={m}
                      className="text-right font-mono text-xs tabular-nums"
                      title={typeof r[`${m}_n`] === 'number' ? `n = ${r[`${m}_n`]}` : undefined}
                    >
                      {fmtMetric(m, r[m])}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {pending.length > 0 && (
        <section className="flex flex-col gap-1.5">
          <h3 className="text-sm font-semibold">{t('results.failed')}</h3>
          <div className="overflow-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('results.col.run')}</TableHead>
                  <TableHead>{t('results.col.technique')}</TableHead>
                  <TableHead>{t('results.col.status')}</TableHead>
                  <TableHead>{t('results.col.error')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pending.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono text-xs">#{r.seq}</TableCell>
                    <TableCell className="text-sm">
                      <TechniqueName name={r.technique} />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={r.status} label={statusLabel(r.status)} />
                    </TableCell>
                    <TableCell className="max-w-2xl whitespace-normal text-xs text-destructive">
                      {r.error ?? '–'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
      )}
    </div>
  )
}
