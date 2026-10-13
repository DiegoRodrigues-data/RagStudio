import { useCallback, useMemo, useState } from 'react'
import { FileText, FolderInput, RefreshCw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Bar } from '@/components/shared/bar'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { DataTable, type DataTableColumn } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { LoadingState } from '@/components/shared/loading-state'
import { PageHeader } from '@/components/shared/page-header'
import { Stat } from '@/components/shared/stat'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type { CorpusDetail, CorpusProfileData, CorpusSummary, DocumentProfile } from '@/lib/types'
import { cn } from '@/lib/utils'
import { DocumentSheet } from './document-sheet'
import { dict } from './i18n'
import { ImportDialog } from './import-dialog'
import { IndicesTab } from './indices-tab'
import { SplitsTab } from './splits-tab'

const pct = (v: number): string => `${(v * 100).toFixed(1)}%`

export default function CorpusPage(): React.JSX.Element {
  const t = usePageT(dict)
  const gt = useT()
  const corpora = useApiData<CorpusSummary[]>(useCallback(() => api.corpus.list(), []))
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [docId, setDocId] = useState<string | null>(null)
  const [filter, setFilter] = useState('')

  const name = selectedName ?? corpora.data?.[0]?.name ?? null
  const detail = useApiData<CorpusDetail>(
    useMemo(() => (name ? () => api.corpus.describe(name) : null), [name])
  )
  const profile = useApiData<CorpusProfileData>(
    useMemo(() => (name ? () => api.corpus.profile(name) : null), [name])
  )
  const d = name ? detail.data : null
  const docs = name ? (profile.data?.documents ?? []) : []

  const splitOf = useMemo(() => {
    const map = new Map<string, string>()
    for (const [split, ids] of Object.entries(d?.split_documents ?? {})) {
      for (const id of ids) map.set(id, split)
    }
    return map
  }, [d])

  const visible = docs.filter((x) => x.doc_id.toLowerCase().includes(filter.trim().toLowerCase()))
  const maxChars = Math.max(1, ...docs.map((x) => x.chars))

  const remove = async (): Promise<void> => {
    if (!name) return
    const res = await api.corpus.delete(name)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('delete.done'))
    setSelectedName(null)
    corpora.reload()
  }

  const columns: DataTableColumn<DocumentProfile>[] = [
    {
      id: 'id',
      header: t('docs.id'),
      cell: (r) => <span className="font-mono text-xs">{r.doc_id}</span>
    },
    ...(
      [
        ['chars', 'docs.chars'],
        ['words', 'docs.words'],
        ['paragraphs', 'docs.paragraphs'],
        ['headings', 'docs.headings']
      ] as const
    ).map(([key, label]) => ({
      id: key,
      header: t(label),
      className: 'text-right font-mono tabular-nums',
      headerClassName: 'text-right',
      cell: (r: DocumentProfile) => r[key].toLocaleString()
    })),
    ...(
      [
        ['table_line_ratio', 'docs.tables'],
        ['digit_ratio', 'docs.digits'],
        ['vocabulary_ratio', 'docs.vocab']
      ] as const
    ).map(([key, label]) => ({
      id: key,
      header: t(label),
      className: 'text-right font-mono tabular-nums',
      headerClassName: 'text-right',
      cell: (r: DocumentProfile) => pct(r[key])
    })),
    { id: 'language', header: t('docs.language'), cell: (r) => r.language },
    { id: 'format', header: t('docs.format'), cell: (r) => r.format },
    {
      id: 'split',
      header: t('docs.split'),
      cell: (r) =>
        splitOf.get(r.doc_id) ? <Badge variant="secondary">{splitOf.get(r.doc_id)}</Badge> : '–'
    }
  ]

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <PageHeader>
        <Button size="sm" onClick={() => setImportOpen(true)}>
          <FolderInput /> {t('actions.import')}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            corpora.reload()
            detail.reload()
            profile.reload()
          }}
        >
          <RefreshCw className={cn(corpora.loading && 'animate-spin')} /> {gt('common.refresh')}
        </Button>
      </PageHeader>

      <ErrorAlert
        title={t('common.errorTitle')}
        message={corpora.error}
        retryLabel={gt('common.retry')}
        onRetry={corpora.reload}
      />

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <div className="flex min-h-48 flex-col rounded-lg border bg-card lg:h-[calc(100svh-11.5rem)]">
          <div className="flex items-center gap-2 border-b px-3 py-2 text-sm font-medium">
            <FileText className="size-4" /> {t('list.title')}
            {corpora.data && <Badge variant="secondary">{corpora.data.length}</Badge>}
          </div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-1 p-2">
              {corpora.loading && !corpora.data && <LoadingState label={gt('common.loading')} />}
              {corpora.data?.length === 0 && (
                <p className="p-3 text-xs text-muted-foreground">{t('list.emptyHint')}</p>
              )}
              {corpora.data?.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelectedName(c.name)}
                  className={cn(
                    'flex flex-col gap-0.5 rounded-md border px-2.5 py-2 text-left text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50',
                    c.name === name
                      ? 'border-primary/40 bg-muted'
                      : 'border-transparent hover:bg-muted/60'
                  )}
                >
                  <span className="truncate font-medium">{c.name}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {t('list.docs', { n: c.documents })} · {c.language || '–'}
                    {typeof c.total_chars === 'number' && ` · ${c.total_chars.toLocaleString()} ch`}
                  </span>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>

        <div className="min-w-0">
          {!name ? (
            <EmptyState
              icon={FileText}
              title={t('list.empty')}
              description={t('list.emptyHint')}
              action={
                <Button size="sm" onClick={() => setImportOpen(true)}>
                  <FolderInput /> {t('actions.import')}
                </Button>
              }
            />
          ) : (
            <Tabs defaultValue="documents" className="gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <TabsList>
                  <TabsTrigger value="documents">
                    {t('tabs.documents')}
                    {docs.length > 0 && (
                      <span className="text-muted-foreground tabular-nums">({docs.length})</span>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="profile">{t('tabs.profile')}</TabsTrigger>
                  <TabsTrigger value="splits">{t('tabs.splits')}</TabsTrigger>
                  <TabsTrigger value="indices">
                    {t('tabs.indices')}
                    {d && d.indices.length > 0 && (
                      <span className="text-muted-foreground tabular-nums">
                        ({d.indices.length})
                      </span>
                    )}
                  </TabsTrigger>
                </TabsList>
                <Button size="sm" variant="ghost" onClick={() => setDeleting(true)}>
                  <Trash2 /> {t('actions.delete')}
                </Button>
              </div>

              <ErrorAlert title={t('common.errorTitle')} message={detail.error ?? profile.error} />

              <TabsContent value="documents" className="flex flex-col gap-3">
                <Input
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder={t('docs.filter')}
                  className="h-8 max-w-xs"
                />
                <DataTable
                  columns={columns}
                  rows={visible}
                  rowKey={(r) => r.doc_id}
                  loading={profile.loading && !profile.data}
                  onRowClick={(r) => setDocId(r.doc_id)}
                  empty={<EmptyState title={t('list.empty')} />}
                />
              </TabsContent>

              <TabsContent value="profile" className="flex flex-col gap-4">
                {d && (
                  <>
                    <p className="text-xs text-muted-foreground">{t('profile.hint')}</p>
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
                      <Stat label={t('profile.documents')} value={d.profile.documents} mono />
                      <Stat
                        label={t('profile.totalChars')}
                        value={d.profile.total_chars.toLocaleString()}
                        mono
                      />
                      <Stat
                        label={t('profile.totalWords')}
                        value={d.profile.total_words.toLocaleString()}
                        mono
                      />
                      <Stat
                        label={t('profile.meanChars')}
                        value={Math.round(d.profile.chars.mean).toLocaleString()}
                        hint={`± ${Math.round(d.profile.chars.stdev).toLocaleString()}`}
                        mono
                      />
                      <Stat
                        label={t('profile.range')}
                        value={`${d.profile.chars.min.toLocaleString()} / ${d.profile.chars.max.toLocaleString()}`}
                        mono
                      />
                      <Stat
                        label={t('profile.languages')}
                        value={Object.entries(d.profile.languages)
                          .map(([k, v]) => `${k} ${v}`)
                          .join(' · ')}
                        hint={Object.entries(d.profile.formats)
                          .map(([k, v]) => `${k} ${v}`)
                          .join(' · ')}
                        mono
                      />
                    </div>
                    <section className="rounded-lg border bg-card p-4">
                      <h3 className="mb-3 text-sm font-semibold">{t('profile.sizeChart')}</h3>
                      <div className="flex max-h-96 flex-col gap-1.5 overflow-auto">
                        {[...docs]
                          .sort((a, b) => b.chars - a.chars)
                          .map((x) => (
                            <Bar
                              key={x.doc_id}
                              label={x.doc_id}
                              value={x.chars}
                              max={maxChars}
                              text={x.chars.toLocaleString()}
                              hint={`${x.words.toLocaleString()} words`}
                            />
                          ))}
                      </div>
                    </section>
                    <div className="grid gap-2 text-xs md:grid-cols-2">
                      <div className="rounded-md border p-2.5">
                        <div className="text-muted-foreground">{t('profile.cleaning')}</div>
                        <div className="font-mono">
                          {d.cleaning.length ? d.cleaning.join(', ') : gt('common.none')}
                        </div>
                      </div>
                      <div className="rounded-md border p-2.5">
                        <div className="text-muted-foreground">{t('profile.hash')}</div>
                        <div className="truncate font-mono" title={d.content_hash}>
                          {d.content_hash}
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </TabsContent>

              <TabsContent value="splits">
                <SplitsTab
                  t={t}
                  corpus={name}
                  splits={d?.split_documents ?? {}}
                  documents={d?.documents ?? []}
                  onChanged={detail.reload}
                  onOpenDocument={setDocId}
                />
              </TabsContent>

              <TabsContent value="indices">
                <IndicesTab
                  key={name}
                  t={t}
                  corpus={name}
                  splits={Object.keys(d?.split_documents ?? {})}
                />
              </TabsContent>
            </Tabs>
          )}
        </div>
      </div>

      <ImportDialog
        t={t}
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={(n) => {
          setSelectedName(n)
          corpora.reload()
        }}
      />
      {name && <DocumentSheet t={t} corpus={name} docId={docId} onClose={() => setDocId(null)} />}
      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title={t('delete.title')}
        description={t('delete.description', { name: name ?? '' })}
        confirmLabel={gt('common.delete')}
        cancelLabel={gt('common.cancel')}
        destructive
        onConfirm={remove}
      />
    </div>
  )
}
