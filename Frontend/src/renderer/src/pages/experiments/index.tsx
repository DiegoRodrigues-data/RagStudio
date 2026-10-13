import { useCallback, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT } from '@/components/shared/use-page-t'
import { useStream } from '@/hooks/use-stream'
import { useStreamDone } from '@/hooks/use-stream-done'
import type { ProgressEvent, RunbookSummary } from '@/lib/types'
import { cn } from '@/lib/utils'
import { AnswerSheet } from './answer-sheet'
import { CompareTab } from './compare-tab'
import { dict } from './i18n'
import { MonitorTab } from './monitor-tab'
import { ResultsTab } from './results-tab'
import { RunSheet } from './run-sheet'
import { RunbookList } from './runbook-list'
import { SetupTab } from './setup-tab'

type Tab = 'setup' | 'monitor' | 'results' | 'compare'

export default function ExperimentsPage(): React.JSX.Element {
  const t = usePageT(dict)
  const runbooks = useApiData<RunbookSummary[]>(useCallback(() => api.experiments.list(), []))
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('setup')
  const [compare, setCompare] = useState<{ a: string | null; b: string | null }>({
    a: null,
    b: null
  })
  const [openRun, setOpenRun] = useState<{ id: string; seq: number } | null>(null)
  const [openAnswer, setOpenAnswer] = useState<number | null>(null)
  const [version, setVersion] = useState(0)

  const stream = useStream<ProgressEvent>()
  const [streamRunbookId, setStreamRunbookId] = useState<string | null>(null)
  const [startedAt, setStartedAt] = useState<number | null>(null)

  useStreamDone(stream, () => {
    runbooks.reload()
    setVersion((v) => v + 1)
  })
  const refreshKey = `${stream.id ?? ''}:${stream.done ? 1 : 0}:${version}`
  const selected = runbooks.data?.find((r) => r.id === selectedId) ?? null

  const startRun = (id: string): void => {
    if (stream.running) return void toast.error(t('busy'))
    setSelectedId(id)
    setStreamRunbookId(id)
    setStartedAt(Date.now())
    setTab('monitor')
    void stream.startWith((sid) => api.experiments.run(sid, id))
  }

  const onCreated = (id: string, run: boolean): void => {
    runbooks.reload()
    setSelectedId(id)
    if (run) startRun(id)
    else setTab('monitor')
  }

  const selectRunbook = (id: string): void => {
    setSelectedId(id)
    setCompare({ a: null, b: null })
    if (tab === 'setup') setTab('results')
  }

  return (
    <div
      className={cn(
        'grid h-full min-h-0 gap-4',
        tab !== 'setup' && 'lg:grid-cols-[17rem_minmax(0,1fr)]'
      )}
    >
      {/* the runbook list gives its width to the form while a new experiment is being configured */}
      <div className={cn('min-h-64 lg:h-[calc(100svh-7.5rem)]', tab === 'setup' && 'hidden')}>
        <RunbookList
          t={t}
          runbooks={runbooks.data}
          loading={runbooks.loading}
          error={runbooks.error}
          selectedId={selectedId}
          onSelect={selectRunbook}
          onReload={runbooks.reload}
          onDeleted={(id) => {
            runbooks.reload()
            if (selectedId === id) setSelectedId(null)
          }}
          onRun={startRun}
          onNew={() => setTab('setup')}
          runningId={stream.running ? streamRunbookId : null}
        />
      </div>
      <div className="min-w-0">
        <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)} className="gap-3">
          <TabsList>
            <TabsTrigger value="setup">{t('tabs.setup')}</TabsTrigger>
            <TabsTrigger value="monitor">
              {t('tabs.monitor')}
              {stream.running && (
                <span className="size-1.5 animate-pulse rounded-full bg-primary" />
              )}
            </TabsTrigger>
            <TabsTrigger value="results">{t('tabs.results')}</TabsTrigger>
            <TabsTrigger value="compare">{t('tabs.compare')}</TabsTrigger>
          </TabsList>
          <TabsContent value="setup">
            <SetupTab t={t} onCreated={onCreated} />
          </TabsContent>
          <TabsContent value="monitor">
            <MonitorTab
              t={t}
              runbook={selected}
              stream={stream}
              streamRunbookId={streamRunbookId}
              startedAt={startedAt}
              onStart={() => selected && startRun(selected.id)}
              onViewResults={() => setTab('results')}
            />
          </TabsContent>
          <TabsContent value="results">
            <ResultsTab
              t={t}
              runbookId={selectedId}
              refreshKey={refreshKey}
              onOpenRun={(id, seq) => setOpenRun({ id, seq })}
              onCompare={(a, b) => {
                setCompare({ a, b })
                setTab('compare')
              }}
            />
          </TabsContent>
          <TabsContent value="compare">
            <CompareTab
              key={selectedId ?? 'none'}
              t={t}
              runbookId={selectedId}
              refreshKey={refreshKey}
              runA={compare.a}
              runB={compare.b}
              onChange={(a, b) => setCompare({ a, b })}
              onOpenAnswer={setOpenAnswer}
            />
          </TabsContent>
        </Tabs>
      </div>

      <RunSheet
        t={t}
        runId={openRun?.id ?? null}
        seq={openRun?.seq}
        onClose={() => setOpenRun(null)}
        onOpenAnswer={setOpenAnswer}
        onChanged={() => {
          runbooks.reload()
          setVersion((v) => v + 1)
        }}
      />
      <AnswerSheet t={t} resultId={openAnswer} onClose={() => setOpenAnswer(null)} />
    </div>
  )
}
