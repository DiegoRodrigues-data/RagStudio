import { useTechniqueTitle } from '@/hooks/use-technique-title'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle
} from '@/components/ui/sheet'
import { Bar } from '@/components/shared/bar'
import { ErrorAlert } from '@/components/shared/error-alert'
import { JsonView } from '@/components/shared/json-view'
import { LoadingState } from '@/components/shared/loading-state'
import {
  GENERATION_METRICS,
  RETRIEVAL_METRICS,
  fmtLatency,
  fmtMetric,
  metricLabel
} from '@/components/shared/metrics'
import { Stat } from '@/components/shared/stat'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type { AnswerDetail } from '@/lib/types'
import { cn } from '@/lib/utils'
import type { ExpKey } from './i18n'

const VERDICTS = ['correct', 'partially', 'incorrect'] as const

export function AnswerSheet({
  t,
  resultId,
  onClose
}: {
  t: PageT<ExpKey>
  resultId: number | null
  onClose: () => void
}): React.JSX.Element {
  const gt = useT()
  const techTitle = useTechniqueTitle()
  const loader = useMemo(
    () => (resultId !== null ? () => api.experiments.answer(resultId) : null),
    [resultId]
  )
  const detail = useApiData<AnswerDetail>(loader)
  const d = resultId !== null ? detail.data : null
  const [note, setNote] = useState('')

  const review = async (verdict: string): Promise<void> => {
    if (resultId === null) return
    const res = await api.evaluate.reviewAdd(resultId, verdict, note.trim())
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('answer.review.saved'))
    setNote('')
  }

  const maxStage = Math.max(0.000001, ...(d?.result.timings ?? []).map((x) => x.seconds))
  const metrics = d?.metrics ?? {}
  const shown = [...RETRIEVAL_METRICS, ...GENERATION_METRICS].filter(
    (m) => metrics[m] !== null && metrics[m] !== undefined
  )

  return (
    <Sheet open={resultId !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 sm:max-w-6xl">
        <SheetHeader>
          <SheetTitle>{t('answer.title', { code: d?.result.question_code ?? '…' })}</SheetTitle>
          <SheetDescription className="font-mono text-xs">
            {d ? `${techTitle(d.run.technique)} · ${d.run.id}` : ''}
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
          <ErrorAlert
            title={gt('common.error')}
            message={resultId !== null ? detail.error : null}
          />
          {detail.loading && !d && <LoadingState rows={8} />}
          {d && (
            <div className="grid items-start gap-4 lg:grid-cols-2">
              <div className="flex min-w-0 flex-col gap-3">
                <Block title={t('answer.question')}>{d.result.question_text}</Block>
                <Block title={t('answer.answer')} strong>
                  {d.result.error ? (
                    <span className="text-destructive">{d.result.error}</span>
                  ) : (
                    d.result.answer
                  )}
                </Block>
                <Block title={t('answer.expected')}>
                  {d.question?.expected_answer || (
                    <span className="text-muted-foreground">{t('answer.noExpected')}</span>
                  )}
                </Block>
                {d.result.warnings.length > 0 && (
                  <Block title={t('answer.warnings')}>
                    <ul className="list-disc pl-4 text-xs text-amber-700 dark:text-amber-400">
                      {d.result.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </Block>
                )}
                <div>
                  <h4 className="mb-1.5 text-xs font-medium">{t('answer.metrics')}</h4>
                  <div className="grid grid-cols-3 gap-2 xl:grid-cols-4">
                    <Stat label="Latency" value={fmtLatency(d.result.latency_total)} mono />
                    <Stat label="LLM calls" value={d.result.llm_calls} mono />
                    <Stat
                      label="Tokens"
                      value={(d.result.prompt_tokens + d.result.completion_tokens).toLocaleString()}
                      mono
                    />
                    {shown.map((m) => (
                      <Stat key={m} label={metricLabel(m)} value={fmtMetric(m, metrics[m])} mono />
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="mb-1.5 text-xs font-medium">{t('answer.timings')}</h4>
                  <div className="flex flex-col gap-1">
                    {d.result.timings.map((x) => (
                      <Bar
                        key={x.stage}
                        label={x.stage}
                        value={x.seconds}
                        max={maxStage}
                        text={fmtLatency(x.seconds)}
                      />
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="mb-1.5 text-xs font-medium">{t('answer.review')}</h4>
                  <div className="flex flex-wrap items-center gap-2">
                    <Input
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      placeholder={t('answer.review.note')}
                      className="h-8 max-w-xs"
                    />
                    {VERDICTS.map((v) => (
                      <Button key={v} variant="outline" size="sm" onClick={() => void review(v)}>
                        {t(`answer.review.${v}`)}
                      </Button>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="mb-1.5 text-xs font-medium">{t('answer.diagnostics')}</h4>
                  <JsonView value={d.result.diagnostics} expandDepth={1} maxHeight="max-h-72" />
                </div>
              </div>

              <div className="flex min-w-0 flex-col gap-3">
                {(d.question?.gold_passages.length ?? 0) > 0 && (
                  <div>
                    <h4 className="mb-1.5 text-xs font-medium">{t('answer.gold')}</h4>
                    <ul className="flex flex-col gap-1.5">
                      {d.question?.gold_passages.map((g, i) => (
                        <li key={i} className="rounded-md border border-dashed p-2 text-xs">
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {g.document_id}
                            {g.char_start !== null && ` [${g.char_start}:${g.char_end}]`}
                          </span>
                          <p className="mt-0.5 leading-relaxed">{g.text}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div>
                  <h4 className="mb-1.5 flex items-center gap-2 text-xs font-medium">
                    {t('answer.chunks')}
                    <Badge variant="secondary">{d.chunks.length}</Badge>
                    <span className="font-normal text-muted-foreground">
                      {d.result.context_chars.toLocaleString()} chars
                    </span>
                    {d.result.context_truncated === 1 && (
                      <Badge variant="outline">{t('answer.truncated')}</Badge>
                    )}
                  </h4>
                  <ol className="flex flex-col gap-2">
                    {d.chunks.map((c) => (
                      <li
                        key={c.rank}
                        className={cn('rounded-md border p-2', c.in_context !== 1 && 'opacity-60')}
                      >
                        <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                          <Badge variant="secondary">#{c.rank}</Badge>
                          <span className="font-mono">{c.chunk_id}</span>
                          <span className="font-mono">score {c.score.toFixed(4)}</span>
                          <span className="font-mono">
                            [{c.char_start}:{c.char_end}]
                          </span>
                          <Badge variant="outline">{c.source}</Badge>
                          {c.in_context === 1 && <span>{t('answer.inContext')}</span>}
                        </div>
                        <p className="text-xs leading-relaxed whitespace-pre-wrap">{c.text}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

function Block({
  title,
  strong,
  children
}: {
  title: string
  strong?: boolean
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div>
      <h4 className="mb-1 text-xs font-medium">{title}</h4>
      <div
        className={cn(
          'rounded-md border p-2.5 text-sm leading-relaxed whitespace-pre-wrap',
          strong ? 'bg-muted/50' : 'text-foreground/90'
        )}
      >
        {children}
      </div>
    </div>
  )
}
