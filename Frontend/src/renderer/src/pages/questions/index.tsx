import { useCallback, useMemo, useState } from 'react'
import {
  Archive,
  CircleQuestionMark,
  Download,
  FileJson,
  Pencil,
  Plus,
  RefreshCw
} from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { DataTable, type DataTableColumn } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { LoadingState } from '@/components/shared/loading-state'
import { metricLabel } from '@/components/shared/metrics'
import { PageHeader } from '@/components/shared/page-header'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type {
  Availability,
  CorpusSummary,
  Question,
  QuestionSetDetail,
  QuestionSetSummary
} from '@/lib/types'
import { cn } from '@/lib/utils'
import { dict } from './i18n'
import { ImportDialog } from './import-dialog'
import { QuestionDialog, type QuestionDialogRequest } from './question-dialog'

/** Metrics that share the same explanation are listed together. */
function ReasonList({ entries }: { entries: Record<string, string> }): React.JSX.Element {
  const byReason = new Map<string, string[]>()
  for (const [metric, why] of Object.entries(entries)) {
    const reason = why.replace(/^computed on /, '')
    byReason.set(reason, [...(byReason.get(reason) ?? []), metricLabel(metric)])
  }
  if (byReason.size === 0) return <p>–</p>
  return (
    <ul className="flex flex-col gap-1.5">
      {[...byReason.entries()].map(([reason, metrics]) => (
        <li key={reason}>
          <span className="font-medium">{metrics.join(', ')}</span>
          <span className="block text-muted-foreground">{reason}</span>
        </li>
      ))}
    </ul>
  )
}

export default function QuestionsPage(): React.JSX.Element {
  const t = usePageT(dict)
  const gt = useT()
  const sets = useApiData<QuestionSetSummary[]>(useCallback(() => api.questions.sets(), []))
  const corpora = useApiData<CorpusSummary[]>(useCallback(() => api.corpus.list(), []))
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  const [filter, setFilter] = useState('')
  const [importOpen, setImportOpen] = useState(false)
  const [editing, setEditing] = useState<QuestionDialogRequest | null>(null)
  const [archiving, setArchiving] = useState<Question | null>(null)

  const name = selectedName ?? sets.data?.[0]?.name ?? null
  const detail = useApiData<QuestionSetDetail>(
    useMemo(
      () => (name ? () => api.questions.list(name, showArchived) : null),
      [name, showArchived]
    )
  )
  const availability = useApiData<Availability>(
    useMemo(() => (name ? () => api.questions.availability(name) : null), [name]),
    detail.data?.questions.length ?? 0
  )

  const reloadAll = (): void => {
    sets.reload()
    detail.reload()
    availability.reload()
  }

  const needle = filter.trim().toLowerCase()
  const rows = (name ? (detail.data?.questions ?? []) : []).filter(
    (q) => !needle || `${q.code} ${q.text}`.toLowerCase().includes(needle)
  )

  const exportSet = async (): Promise<void> => {
    if (!name) return
    const output = await window.api.saveFile(`${name}.json`, [
      { name: 'JSON', extensions: ['json'] }
    ])
    if (!output) return
    const res = await api.questions.export(name, output)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('actions.exported', { n: res.data.questions }))
  }

  const archive = async (): Promise<void> => {
    if (!archiving) return
    const res = await api.questions.archive(archiving.id)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('archive.done'))
    reloadAll()
  }

  const columns: DataTableColumn<Question>[] = [
    {
      id: 'code',
      header: t('col.code'),
      cell: (q) => (
        <span className="flex items-center gap-1.5 font-mono text-xs font-medium">
          {q.code}
          {q.version > 1 && <Badge variant="outline">v{q.version}</Badge>}
          {q.archived_at && <Badge variant="secondary">{t('row.archived')}</Badge>}
        </span>
      )
    },
    {
      id: 'text',
      header: t('col.text'),
      className: 'max-w-xl whitespace-normal text-sm',
      cell: (q) => q.text
    },
    {
      id: 'expected',
      header: t('col.expected'),
      className: 'max-w-sm whitespace-normal text-xs text-muted-foreground',
      cell: (q) => q.expected_answer || '–'
    },
    {
      id: 'gold',
      header: t('col.gold'),
      className: 'text-right font-mono tabular-nums',
      headerClassName: 'text-right',
      cell: (q) => (q.gold_passages.length > 0 ? q.gold_passages.length : '–')
    },
    {
      id: 'type',
      header: t('col.type'),
      cell: (q) => <span className="text-xs">{q.answer_type}</span>
    },
    {
      id: 'split',
      header: t('col.split'),
      cell: (q) => (q.split ? <Badge variant="secondary">{q.split}</Badge> : '–')
    },
    {
      id: 'actions',
      header: '',
      className: 'w-20',
      cell: (q) =>
        q.archived_at ? null : (
          <span className="flex justify-end gap-0.5">
            <Button
              variant="ghost"
              size="icon-xs"
              aria-label={t('row.edit')}
              title={t('row.edit')}
              onClick={() => name && setEditing({ question: q, setName: name })}
            >
              <Pencil />
            </Button>
            <Button
              variant="ghost"
              size="icon-xs"
              aria-label={t('row.archive')}
              title={t('row.archive')}
              onClick={() => setArchiving(q)}
            >
              <Archive />
            </Button>
          </span>
        )
    }
  ]

  const av = name ? availability.data : null

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <PageHeader>
        <Button size="sm" onClick={() => setImportOpen(true)}>
          <FileJson /> {t('actions.import')}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setEditing({ question: null, setName: name ?? '' })}
        >
          <Plus /> {t('actions.new')}
        </Button>
        <Button size="sm" variant="outline" disabled={!name} onClick={() => void exportSet()}>
          <Download /> {t('actions.export')}
        </Button>
        <Button size="sm" variant="ghost" onClick={reloadAll}>
          <RefreshCw className={cn(sets.loading && 'animate-spin')} /> {gt('common.refresh')}
        </Button>
      </PageHeader>

      <ErrorAlert
        title={t('errorTitle')}
        message={sets.error ?? (name ? detail.error : null)}
        retryLabel={gt('common.retry')}
        onRetry={reloadAll}
      />

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <div className="flex min-h-48 flex-col rounded-lg border bg-card lg:h-[calc(100svh-11.5rem)]">
          <div className="flex items-center gap-2 border-b px-3 py-2 text-sm font-medium">
            <CircleQuestionMark className="size-4" /> {t('sets.title')}
            {sets.data && <Badge variant="secondary">{sets.data.length}</Badge>}
          </div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-1 p-2">
              {sets.loading && !sets.data && <LoadingState label={gt('common.loading')} />}
              {sets.data?.length === 0 && (
                <p className="p-3 text-xs text-muted-foreground">{t('sets.emptyHint')}</p>
              )}
              {sets.data?.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSelectedName(s.name)}
                  className={cn(
                    'flex flex-col gap-0.5 rounded-md border px-2.5 py-2 text-left text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50',
                    s.name === name
                      ? 'border-primary/40 bg-muted'
                      : 'border-transparent hover:bg-muted/60'
                  )}
                >
                  <span className="truncate font-medium">{s.name}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {t('sets.count', { n: s.questions })}
                    {s.language && ` · ${s.language}`}
                  </span>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>

        <div className="flex min-w-0 flex-col gap-4">
          {!name ? (
            <EmptyState
              icon={CircleQuestionMark}
              title={t('sets.empty')}
              description={t('sets.emptyHint')}
              action={
                <Button size="sm" onClick={() => setImportOpen(true)}>
                  <FileJson /> {t('actions.import')}
                </Button>
              }
            />
          ) : (
            <>
              {av && (
                <section className="rounded-lg border bg-card p-3">
                  <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                    <h3 className="text-sm font-semibold">{t('avail.title')}</h3>
                    <span className="text-xs text-muted-foreground">
                      {t('avail.summary', {
                        n: av.questions,
                        gold: av.with_gold_passages,
                        expected: av.with_expected_answer
                      })}
                    </span>
                  </div>
                  <div className="grid gap-3 text-xs md:grid-cols-3">
                    <div>
                      <div className="mb-1 text-muted-foreground">{t('avail.measured')}</div>
                      <div className="flex flex-wrap gap-1">
                        {av.available
                          .filter((m) => !(m in av.partial))
                          .map((m) => (
                            <Badge key={m} variant="secondary">
                              {metricLabel(m)}
                            </Badge>
                          ))}
                      </div>
                    </div>
                    <div>
                      <div className="mb-1 text-muted-foreground">{t('avail.partial')}</div>
                      <ReasonList entries={av.partial} />
                    </div>
                    <div>
                      <div className="mb-1 text-muted-foreground">{t('avail.missing')}</div>
                      <ReasonList entries={av.requires_annotation} />
                    </div>
                  </div>
                  <p className="mt-2 text-[11px] text-muted-foreground">{t('avail.hint')}</p>
                </section>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <Input
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder={t('filter.placeholder')}
                  className="h-8 max-w-xs"
                />
                <label className="flex items-center gap-2 text-xs">
                  <Switch checked={showArchived} onCheckedChange={setShowArchived} />
                  {t('filter.archived')}
                </label>
              </div>
              <DataTable
                columns={columns}
                rows={rows}
                rowKey={(q) => q.id}
                loading={detail.loading && !detail.data}
                empty={<EmptyState title={t('sets.empty')} />}
              />
            </>
          )}
        </div>
      </div>

      <ImportDialog
        t={t}
        open={importOpen}
        onOpenChange={setImportOpen}
        corpora={corpora.data ?? []}
        onImported={(n) => {
          setSelectedName(n)
          reloadAll()
        }}
      />
      {editing && (
        <QuestionDialog
          key={editing.question?.id ?? 'new'}
          t={t}
          request={editing}
          corpora={corpora.data ?? []}
          onClose={() => setEditing(null)}
          onSaved={(n) => {
            setSelectedName(n)
            reloadAll()
          }}
        />
      )}
      <ConfirmDialog
        open={archiving !== null}
        onOpenChange={(o) => !o && setArchiving(null)}
        title={t('archive.title')}
        description={t('archive.description', { code: archiving?.code ?? '' })}
        confirmLabel={t('row.archive')}
        cancelLabel={gt('common.cancel')}
        onConfirm={archive}
      />
    </div>
  )
}
