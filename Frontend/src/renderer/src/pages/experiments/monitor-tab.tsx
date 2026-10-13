import { useTechniqueTitle } from '@/hooks/use-technique-title'
import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, LoaderCircle, Play, Square } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EmptyState } from '@/components/shared/empty-state'
import { fmtSeconds, shortId } from '@/components/shared/exp-format'
import { StatusBadge } from '@/components/shared/exp-status-badge'
import { fmtLatency, fmtMetric } from '@/components/shared/metrics'
import { Stat } from '@/components/shared/stat'
import type { PageT } from '@/components/shared/use-page-t'
import { useStatusLabel } from '@/components/shared/use-status-label'
import type { UseStream } from '@/hooks/use-stream'
import type { ProgressEvent, ProgressPayload, RunbookSummary } from '@/lib/types'
import { cn } from '@/lib/utils'
import type { ExpKey } from './i18n'

interface Snapshot {
  totalRuns: number
  finishedRuns: number
  failedRuns: number
  currentRun: string | null
  technique: string | null
  question: string | null
  questionPos: number
  questionOf: number
  indexing: string | null
  spent: number
  budgetWarning: boolean
  summary: ProgressPayload | null
}

function reduce(events: ProgressEvent[]): Snapshot {
  const s: Snapshot = {
    totalRuns: 0,
    finishedRuns: 0,
    failedRuns: 0,
    currentRun: null,
    technique: null,
    question: null,
    questionPos: 0,
    questionOf: 0,
    indexing: null,
    spent: 0,
    budgetWarning: false,
    summary: null
  }
  for (const { progress: e } of events) {
    if (!e) continue
    switch (e.event) {
      case 'runbook_started':
        s.totalRuns = e.runs ?? 0
        break
      case 'run_skipped':
        s.finishedRuns += 1
        break
      case 'run_started':
        s.currentRun = e.run_id ?? null
        s.technique = e.technique ?? null
        s.questionPos = 0
        s.questionOf = 0
        s.question = null
        s.indexing = null
        break
      case 'chunked':
      case 'embedded':
      case 'enriched':
        s.indexing = `${e.event}${typeof e.done === 'number' ? ` ${e.done}/${e.total}` : ''}`
        break
      case 'persisted':
        s.indexing = null
        break
      case 'question_done':
        s.indexing = null
        s.question = e.question ?? null
        s.questionPos = e.position ?? 0
        s.questionOf = e.of ?? 0
        break
      case 'run_finished':
        s.finishedRuns += 1
        if (e.status === 'failed') s.failedRuns += 1
        if (typeof e.spent_usd === 'number') s.spent = e.spent_usd
        s.questionPos = 0
        s.questionOf = 0
        break
      case 'budget_warning':
        s.budgetWarning = true
        break
      case 'runbook_finished':
        s.summary = e
        if (typeof e.spent_usd === 'number') s.spent = e.spent_usd
        break
    }
  }
  return s
}

function describe(e: ProgressPayload, title: (name: string) => string): string {
  switch (e.event) {
    case 'run_started':
      return `${e.position}/${e.of} · ${title(String(e.technique ?? ''))} · ${shortId(e.run_id, 14)}`
    case 'question_done':
      return `${e.question} (${e.position}/${e.of}) · ${fmtLatency(e.latency)}${e.failed ? ' · FAILED' : ''}`
    case 'run_finished':
      return `${e.status}${e.error ? ` · ${e.error}` : ''}${e.index_reused ? ' · index reused' : ''}`
    case 'run_skipped':
      return `${shortId(e.run_id, 14)} · ${e.reason ?? ''}`
    case 'runbook_started':
      return `${e.runs} runs`
    case 'runbook_finished':
      return `${e.status} · ${e.completed} completed · ${e.failed} failed · ${e.skipped} skipped`
    case 'chunked':
      return `${e.chunks} chunks · ${e.documents} documents`
    case 'embedded':
    case 'enriched':
      return `${e.done}/${e.total}`
    default:
      return ''
  }
}

interface Props {
  t: PageT<ExpKey>
  runbook: RunbookSummary | null
  stream: UseStream<ProgressEvent>
  /** Runbook the current stream belongs to (may differ from the selected one). */
  streamRunbookId: string | null
  startedAt: number | null
  onStart: () => void
  onViewResults: () => void
}

export function MonitorTab({
  t,
  runbook,
  stream,
  streamRunbookId,
  startedAt,
  onStart,
  onViewResults
}: Props): React.JSX.Element {
  const statusLabel = useStatusLabel()
  const techTitle = useTechniqueTitle()
  const [now, setNow] = useState(() => Date.now())
  const [cancelling, setCancelling] = useState(false)
  const mine = !!runbook && streamRunbookId === runbook.id
  const running = mine && stream.running
  const snap = useMemo(() => reduce(mine ? stream.events : []), [mine, stream.events])

  useEffect(() => {
    if (!running) return
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [running])

  if (!runbook) return <EmptyState title={t('monitor.noRunbook')} />

  const fraction = snap.questionOf > 0 ? snap.questionPos / snap.questionOf : 0
  const pct =
    snap.totalRuns > 0
      ? Math.min(100, ((snap.finishedRuns + (running ? fraction : 0)) / snap.totalRuns) * 100)
      : 0
  const elapsed = mine && startedAt ? (now - startedAt) / 1000 : undefined
  const finished = mine && stream.done
  const finalStatus = snap.summary?.status ?? runbook.status
  const budget = runbook.max_budget_usd

  const cancel = async (): Promise<void> => {
    setCancelling(true)
    try {
      await stream.cancel()
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="min-w-0">
            <CardTitle className="truncate text-base">{runbook.name}</CardTitle>
            <p className="font-mono text-xs text-muted-foreground">{runbook.id}</p>
            <p className="mt-1 text-xs text-muted-foreground">{t('monitor.resumeHint')}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge
              status={running ? 'running' : finalStatus}
              label={statusLabel(running ? 'running' : finalStatus)}
            />
            {running ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => void cancel()}
                disabled={cancelling}
              >
                {cancelling ? <LoaderCircle className="animate-spin" /> : <Square />}
                {cancelling ? t('monitor.cancelling') : t('monitor.cancel')}
              </Button>
            ) : (
              <Button size="sm" onClick={onStart} disabled={stream.running}>
                <Play /> {t('monitor.start')}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium">{t('monitor.progress')}</span>
              <span className="font-mono text-muted-foreground">
                {mine && snap.totalRuns > 0
                  ? `${snap.finishedRuns}/${snap.totalRuns} runs · ${pct.toFixed(0)}%`
                  : `${runbook.completed}/${runbook.runs} runs`}
              </span>
            </div>
            <Progress
              value={
                mine && snap.totalRuns > 0
                  ? pct
                  : (runbook.completed / Math.max(1, runbook.runs)) * 100
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
            <Stat
              label={t('monitor.currentRun')}
              value={running && snap.technique ? techTitle(snap.technique) : '–'}
              hint={running && snap.currentRun ? shortId(snap.currentRun, 14) : undefined}
              mono
            />
            <Stat
              label={snap.indexing ? t('monitor.indexing') : t('monitor.question')}
              value={
                snap.indexing ??
                (running && snap.questionOf > 0
                  ? `${snap.question} · ${snap.questionPos}/${snap.questionOf}`
                  : '–')
              }
              mono
            />
            <Stat label={t('monitor.elapsed')} value={running ? fmtSeconds(elapsed) : '–'} mono />
            <Stat
              label={`${t('monitor.spent')} / ${budget != null ? fmtMetric('cost_usd', budget) : t('monitor.noBudget')}`}
              value={fmtMetric('cost_usd', mine ? snap.spent : runbook.cost_usd)}
              mono
            />
            <Stat
              label={t('monitor.failed')}
              value={mine ? snap.failedRuns : '–'}
              mono
              className={cn(mine && snap.failedRuns > 0 && 'border-destructive text-destructive')}
            />
          </div>

          {mine && snap.budgetWarning && (
            <Alert>
              <AlertTriangle />
              <AlertTitle>{t('monitor.budgetWarning')}</AlertTitle>
            </Alert>
          )}
          {mine && (stream.error || (stream.result && !stream.result.ok)) && (
            <Alert variant="destructive">
              <AlertTitle>
                {stream.error ?? (stream.result && !stream.result.ok ? stream.result.error : '')}
              </AlertTitle>
            </Alert>
          )}
          {finished && (
            <Alert>
              <AlertTitle className="flex items-center gap-2">
                {t('monitor.done')}
                <StatusBadge status={finalStatus} label={statusLabel(finalStatus)} />
              </AlertTitle>
              <AlertDescription className="flex flex-col gap-2">
                {snap.summary && (
                  <span className="font-mono text-xs">
                    {t('monitor.summary', {
                      completed: snap.summary.completed ?? 0,
                      skipped: snap.summary.skipped ?? 0,
                      failed: (snap.summary.failed as unknown as number) ?? 0
                    })}
                  </span>
                )}
                <div>
                  <Button size="sm" variant="outline" onClick={onViewResults}>
                    {t('monitor.viewResults')}
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            {t('monitor.log')}
            {mine && <Badge variant="secondary">{stream.events.length}</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[calc(100svh-19rem)] min-h-64 rounded-md border bg-muted/40">
            <div className="p-2 font-mono text-[11px] leading-5">
              {(!mine || stream.events.length === 0) && (
                <div className="text-muted-foreground">{t('monitor.logEmpty')}</div>
              )}
              {mine &&
                stream.events
                  .slice(-400)
                  .reverse()
                  .map((ev, i) => {
                    const e = ev.progress
                    if (!e) return null
                    const bad = e.failed === true || e.status === 'failed'
                    return (
                      <div key={stream.events.length - i} className="flex gap-2">
                        <span
                          className={cn(
                            'w-32 shrink-0',
                            bad
                              ? 'text-destructive'
                              : e.event.startsWith('run')
                                ? 'text-foreground'
                                : 'text-muted-foreground'
                          )}
                        >
                          {e.event}
                        </span>
                        <span className={cn('min-w-0 break-words', bad && 'text-destructive')}>
                          {describe(e, techTitle)}
                        </span>
                      </div>
                    )
                  })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}
