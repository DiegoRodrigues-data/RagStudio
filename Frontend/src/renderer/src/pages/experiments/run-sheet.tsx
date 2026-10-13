import { useTechniqueTitle } from '@/hooks/use-technique-title'
import { useMemo, useState } from 'react'
import { Copy, Gavel, LoaderCircle, RefreshCcw, ShieldAlert, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DataTable, type DataTableColumn } from '@/components/shared/data-table'
import { ErrorAlert } from '@/components/shared/error-alert'
import { JsonView } from '@/components/shared/json-view'
import { LoadingState } from '@/components/shared/loading-state'
import { ALL_METRICS, fmtLatency, fmtMetric, metricLabel } from '@/components/shared/metrics'
import { MockBadge } from '@/components/shared/mock-notice'
import { Stat } from '@/components/shared/stat'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type { EvidencePage, RunAnswerRow, RunDetail } from '@/lib/types'
import { cn } from '@/lib/utils'
import type { ExpKey } from './i18n'

export function RunSheet({
  t,
  runId,
  seq,
  onClose,
  onOpenAnswer,
  onChanged
}: {
  t: PageT<ExpKey>
  runId: string | null
  seq?: number
  onClose: () => void
  onOpenAnswer: (resultId: number) => void
  /** Called after an action that changes stored data (re-evaluation, replica). */
  onChanged: () => void
}): React.JSX.Element {
  const gt = useT()
  const techTitle = useTechniqueTitle()
  const loader = useMemo(() => (runId ? () => api.experiments.show(runId) : null), [runId])
  const detail = useApiData<RunDetail>(loader)
  const evidenceLoader = useMemo(
    () => (runId ? () => api.experiments.evidence(runId, undefined, 0, 150) : null),
    [runId]
  )
  const evidence = useApiData<EvidencePage>(evidenceLoader)
  const [busy, setBusy] = useState<string | null>(null)
  const [dry, setDry] = useState<unknown>(null)
  const d = runId ? detail.data : null

  const act = async (name: string, fn: () => Promise<void>): Promise<void> => {
    setBusy(name)
    try {
      await fn()
    } finally {
      setBusy(null)
    }
  }

  const reevaluate = (judge: boolean): Promise<void> =>
    act(judge ? 'judge' : 'eval', async () => {
      if (!runId) return
      const res = await api.evaluate.rerun(runId, judge)
      if (!res.ok) return void toast.error(res.error)
      toast.success(t('run.reevaluated', { v: res.data.eval_version }))
      detail.reload()
      onChanged()
    })

  const reproduce = (dryRun: boolean): Promise<void> =>
    act(dryRun ? 'dry' : 'repro', async () => {
      if (!runId) return
      const res = await api.experiments.reproduce(runId, dryRun)
      if (!res.ok) return void toast.error(res.error)
      if (dryRun) return setDry(res.data)
      toast.success(
        t('run.reproduced', {
          same: String(res.data.identical_answers ?? '?'),
          total: String(res.data.questions ?? '?')
        })
      )
      onChanged()
    })

  const metrics = d?.metrics ?? {}
  const measured = ALL_METRICS.filter((m) => metrics[m] !== null && metrics[m] !== undefined)
  const stages = (metrics.latency_by_stage ?? {}) as Record<string, number>
  const missing = d?.availability?.requires_annotation ?? {}

  const columns: DataTableColumn<RunAnswerRow>[] = [
    {
      id: 'q',
      header: t('run.answers.question'),
      className: 'w-72 max-w-72 whitespace-normal',
      cell: (r) => (
        <div>
          <span className="font-mono text-xs font-medium">{r.question}</span>
          <p className="line-clamp-2 text-xs text-muted-foreground">{r.text}</p>
        </div>
      )
    },
    {
      id: 'a',
      header: t('run.answers.answer'),
      className: 'whitespace-normal text-xs',
      cell: (r) =>
        r.error ? (
          <span className="text-destructive">{r.error}</span>
        ) : (
          <span className="line-clamp-3">{r.answer}</span>
        )
    },
    {
      id: 'lat',
      header: 'Latency',
      className: 'text-right font-mono text-xs tabular-nums',
      headerClassName: 'text-right',
      cell: (r) => fmtLatency(r.latency)
    },
    {
      id: 'calls',
      header: t('run.answers.calls'),
      className: 'text-right font-mono text-xs tabular-nums',
      headerClassName: 'text-right',
      cell: (r) => r.llm_calls
    }
  ]

  return (
    <Sheet open={runId !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 sm:max-w-5xl">
        <SheetHeader>
          <SheetTitle className="flex flex-wrap items-center gap-2">
            {t('run.title', { seq: seq ?? '', technique: d ? techTitle(d.run.technique) : '…' })}
            <MockBadge provider={d?.run.config.provider} />
          </SheetTitle>
          <SheetDescription className="font-mono text-xs">{runId}</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
          <ErrorAlert title={gt('common.error')} message={runId ? detail.error : null} />
          {detail.loading && !d && <LoadingState rows={8} />}
          {d && (
            <Tabs defaultValue="summary" className="gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <TabsList>
                  <TabsTrigger value="summary">{t('run.tab.summary')}</TabsTrigger>
                  <TabsTrigger value="answers">
                    {t('run.tab.answers')}
                    <span className="text-muted-foreground tabular-nums">({d.answers.length})</span>
                  </TabsTrigger>
                  <TabsTrigger value="evidence">{t('run.tab.evidence')}</TabsTrigger>
                </TabsList>
                <div className="flex flex-wrap gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!!busy}
                    onClick={() => void reevaluate(false)}
                  >
                    {busy === 'eval' ? <LoaderCircle className="animate-spin" /> : <RefreshCcw />}
                    {t('run.reevaluate')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!!busy}
                    onClick={() => void reevaluate(true)}
                  >
                    {busy === 'judge' ? <LoaderCircle className="animate-spin" /> : <Gavel />}
                    {t('run.reevaluateJudge')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!!busy}
                    onClick={() => void reproduce(false)}
                  >
                    {busy === 'repro' ? <LoaderCircle className="animate-spin" /> : <Copy />}
                    {t('run.reproduce')}
                  </Button>
                </div>
              </div>

              <TabsContent value="summary" className="grid items-start gap-4 lg:grid-cols-2">
                <div className="flex min-w-0 flex-col gap-3">
                  <h4 className="text-xs font-medium">{t('run.metrics')}</h4>
                  <div className="grid grid-cols-3 gap-2">
                    {measured.map((m) => (
                      <Stat
                        key={m}
                        label={metricLabel(m)}
                        value={fmtMetric(m, metrics[m])}
                        hint={
                          typeof metrics[`${m}_n`] === 'number'
                            ? `n = ${metrics[`${m}_n`]}`
                            : undefined
                        }
                        mono
                      />
                    ))}
                  </div>
                  {Object.keys(stages).length > 0 && (
                    <div className="grid grid-cols-3 gap-2">
                      {Object.entries(stages).map(([stage, seconds]) => (
                        <Stat
                          key={stage}
                          label={`Latency · ${stage}`}
                          value={fmtLatency(seconds)}
                          mono
                        />
                      ))}
                    </div>
                  )}
                  {Object.keys(missing).length > 0 && (
                    <div className="rounded-md border border-dashed p-2.5 text-xs">
                      <div className="mb-1 font-medium">{t('run.notMeasured')}</div>
                      <ul className="flex flex-col gap-0.5 text-muted-foreground">
                        {Object.entries(missing).map(([m, why]) => (
                          <li key={m}>
                            <span className="font-medium text-foreground">{metricLabel(m)}</span>:{' '}
                            {why}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <div className="flex min-w-0 flex-col gap-3">
                  <h4 className="text-xs font-medium">{t('run.config')}</h4>
                  <JsonView value={d.run.config} maxHeight="max-h-[28rem]" />
                  <div className="flex flex-wrap gap-1.5 text-[11px]">
                    <Badge variant="outline" className="font-mono">
                      config {d.run.config_hash.slice(0, 12)}
                    </Badge>
                    {d.run.index_hash && (
                      <Badge variant="outline" className="font-mono">
                        index {d.run.index_hash.slice(0, 12)}
                      </Badge>
                    )}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="answers">
                <DataTable
                  columns={columns}
                  rows={d.answers}
                  rowKey={(r) => String(r.id)}
                  onRowClick={(r) => onOpenAnswer(r.id)}
                />
              </TabsContent>

              <TabsContent value="evidence" className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={d.evidence.ok ? 'secondary' : 'destructive'}
                    className={cn(d.evidence.ok && 'text-emerald-700 dark:text-emerald-400')}
                  >
                    {d.evidence.ok ? <ShieldCheck /> : <ShieldAlert />}
                    {d.evidence.ok
                      ? t('run.chain.ok', { n: d.evidence.events })
                      : t('run.chain.broken', { seq: d.evidence.broken_at_seq ?? '?' })}
                  </Badge>
                  {d.evidence.head && (
                    <span className="font-mono text-[11px] text-muted-foreground">
                      head {d.evidence.head.slice(0, 24)}…
                    </span>
                  )}
                  <Button
                    variant="outline"
                    size="xs"
                    disabled={!!busy}
                    onClick={() => void reproduce(true)}
                  >
                    {t('run.reproduceDry')}
                  </Button>
                </div>
                {dry !== null && <JsonView value={dry} expandDepth={1} maxHeight="max-h-72" />}
                <div className="grid items-start gap-3 lg:grid-cols-2">
                  <div className="min-w-0">
                    <h4 className="mb-1 text-xs font-medium">{t('run.environment')}</h4>
                    <JsonView value={d.environment} maxHeight="max-h-96" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="mb-1 text-xs font-medium">
                      {evidence.data
                        ? t('run.events.more', {
                            n: evidence.data.events.length,
                            total: evidence.data.total
                          })
                        : '…'}
                    </h4>
                    <ol className="flex max-h-96 flex-col gap-1 overflow-auto rounded-md border bg-muted/40 p-2 font-mono text-[11px]">
                      {(evidence.data?.events ?? []).map((e) => (
                        <li key={e.seq}>
                          <details>
                            <summary className="cursor-pointer">
                              <span className="text-muted-foreground">#{e.seq}</span> {e.kind}
                              {typeof e.payload.task === 'string' && ` · ${e.payload.task}`}
                              <span className="text-muted-foreground">
                                {' '}
                                · {e.chain_sha256.slice(0, 10)}
                              </span>
                            </summary>
                            <pre className="mt-1 max-h-60 overflow-auto rounded bg-background p-2 whitespace-pre-wrap">
                              {JSON.stringify(e.payload, null, 2)}
                            </pre>
                          </details>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
