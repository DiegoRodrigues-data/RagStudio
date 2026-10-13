import { useCallback, useMemo, useState } from 'react'
import { Copy, Download, FileChartColumn, Images, LoaderCircle, Save, Table2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DataTable, type DataTableColumn } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { fmtDate, shortHash } from '@/components/shared/exp-format'
import { FieldRow } from '@/components/shared/field-row'
import { PageHeader } from '@/components/shared/page-header'
import { PathActions } from '@/components/shared/path-actions'
import { RunbookPicker } from '@/components/shared/runbook-picker'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT, type PageT } from '@/components/shared/use-page-t'
import { useLanguage } from '@/hooks/use-t'
import { localUrl } from '@/lib/format'
import type { ExportRow, FiguresResult, RunbookSummary } from '@/lib/types'
import { dict, type RepKey } from './i18n'

const AXES = ['technique', 'chunking', 'retrieval_mode', 'reranker', 'k', 'llm', 'embedding_model']

function ReportTab({
  t,
  ids,
  onDone
}: {
  t: PageT<RepKey>
  ids: string[]
  onDone: () => void
}): React.JSX.Element {
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ path: string; skipped_figures: string[] } | null>(null)
  const generate = async (): Promise<void> => {
    setBusy(true)
    const res = await api.reports.html(ids, undefined, title.trim() || undefined)
    setBusy(false)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('report.done', { n: res.data.figures }))
    setResult(res.data)
    onDone()
  }
  return (
    <section className="flex max-w-3xl flex-col gap-3 rounded-lg border bg-card p-4">
      <div>
        <h3 className="text-sm font-semibold">{t('report.title')}</h3>
        <p className="text-xs text-muted-foreground">{t('report.description')}</p>
      </div>
      <FieldRow label={t('report.name')}>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="RagStudio report"
        />
      </FieldRow>
      <Button onClick={() => void generate()} disabled={busy} className="w-fit">
        {busy ? <LoaderCircle className="animate-spin" /> : <FileChartColumn />}
        {t('report.generate')}
      </Button>
      {result && (
        <div className="flex flex-col gap-2 rounded-md border bg-muted/40 p-2.5">
          <span className="font-mono text-xs break-all">{result.path}</span>
          <PathActions path={result.path} size="sm" />
          {result.skipped_figures.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {t('report.skipped')}: {result.skipped_figures.join('; ')}
            </p>
          )}
        </div>
      )}
    </section>
  )
}

function FiguresTab({ t, ids }: { t: PageT<RepKey>; ids: string[] }): React.JSX.Element {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<FiguresResult | null>(null)
  const generate = async (): Promise<void> => {
    setBusy(true)
    const res = await api.reports.figures(ids)
    setBusy(false)
    if (!res.ok) return void toast.error(res.error)
    setResult(res.data)
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{t('figures.title')}</h3>
          <p className="text-xs text-muted-foreground">{t('figures.description')}</p>
        </div>
        <div className="flex items-center gap-2">
          {result && <PathActions path={result.directory} size="sm" />}
          <Button onClick={() => void generate()} disabled={busy}>
            {busy ? <LoaderCircle className="animate-spin" /> : <Images />}
            {t('figures.generate')}
          </Button>
        </div>
      </div>
      {!result ? (
        <EmptyState icon={Images} title={t('figures.empty')} />
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-2">
            {result.figures.map((f) => (
              <figure key={f.png} className="flex flex-col gap-2 rounded-lg border bg-card p-3">
                <img
                  src={localUrl(f.png)}
                  alt={f.caption}
                  className="w-full rounded-md border bg-white"
                />
                <figcaption className="text-xs text-muted-foreground">{f.caption}</figcaption>
                <div className="flex flex-wrap gap-1">
                  {(['png', 'svg', 'pdf'] as const).map((ext) => (
                    <Button
                      key={ext}
                      variant="outline"
                      size="xs"
                      onClick={() => void window.api.openPath(f[ext])}
                    >
                      {ext.toUpperCase()}
                    </Button>
                  ))}
                </div>
              </figure>
            ))}
          </div>
          {result.skipped.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {t('figures.skipped')}: {result.skipped.join('; ')}
            </p>
          )}
        </>
      )}
    </div>
  )
}

function TablesTab({ t, ids }: { t: PageT<RepKey>; ids: string[] }): React.JSX.Element {
  const [format, setFormat] = useState('markdown')
  const [by, setBy] = useState('technique')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const generate = async (output?: string): Promise<void> => {
    setBusy(true)
    const res = await api.reports.tables(ids, format, by, output)
    setBusy(false)
    if (!res.ok) return void toast.error(res.error)
    setText(res.data.text)
    if (output) toast.success(t('tables.saved'))
  }
  const save = async (): Promise<void> => {
    const ext = format === 'latex' ? 'tex' : format === 'csv' ? 'csv' : 'md'
    const output = await window.api.saveFile(`results.${ext}`)
    if (output) await generate(output)
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <FieldRow label={t('tables.format')}>
          <Select value={format} onValueChange={setFormat}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="markdown">Markdown</SelectItem>
              <SelectItem value="latex">LaTeX</SelectItem>
              <SelectItem value="csv">CSV</SelectItem>
            </SelectContent>
          </Select>
        </FieldRow>
        <FieldRow label={t('tables.by')}>
          <Select value={by} onValueChange={setBy}>
            <SelectTrigger className="w-44">
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
        <Button onClick={() => void generate()} disabled={busy}>
          {busy ? <LoaderCircle className="animate-spin" /> : <Table2 />}
          {t('tables.generate')}
        </Button>
        <Button
          variant="outline"
          disabled={!text}
          onClick={() =>
            void navigator.clipboard.writeText(text).then(() => toast.success(t('tables.copied')))
          }
        >
          <Copy /> Copy
        </Button>
        <Button variant="outline" onClick={() => void save()} disabled={busy}>
          <Save /> {t('tables.save')}
        </Button>
      </div>
      <pre className="min-h-48 overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-xs leading-relaxed">
        {text || t('tables.title')}
      </pre>
    </div>
  )
}

function ExportsTab({
  t,
  ids,
  exports,
  onDone
}: {
  t: PageT<RepKey>
  ids: string[]
  exports: ExportRow[]
  onDone: () => void
}): React.JSX.Element {
  const { language } = useLanguage()
  const [table, setTable] = useState('questions')
  const [format, setFormat] = useState('csv')
  const [busy, setBusy] = useState(false)
  const run = async (): Promise<void> => {
    setBusy(true)
    const res = await api.reports.export(ids, table, format)
    setBusy(false)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('exports.done', { n: res.data.rows }))
    onDone()
  }
  const columns: DataTableColumn<ExportRow>[] = [
    {
      id: 'kind',
      header: t('exports.kind'),
      cell: (r) => <span className="font-mono text-xs">{r.kind}</span>
    },
    {
      id: 'path',
      header: t('exports.path'),
      className: 'max-w-xl',
      cell: (r) => (
        <span className="block truncate font-mono text-xs" title={r.path}>
          {r.path.split('/').slice(-2).join('/')}
        </span>
      )
    },
    {
      id: 'hash',
      header: t('exports.hash'),
      cell: (r) => <span className="font-mono text-xs">{shortHash(r.sha256, 12)}</span>
    },
    {
      id: 'created',
      header: t('exports.created'),
      cell: (r) => <span className="text-xs">{fmtDate(r.created_at, language)}</span>
    },
    { id: 'actions', header: '', cell: (r) => <PathActions path={r.path} /> }
  ]
  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-3 rounded-lg border bg-card p-4">
        <div>
          <h3 className="text-sm font-semibold">{t('exports.title')}</h3>
          <p className="text-xs text-muted-foreground">{t('exports.description')}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <FieldRow label={t('exports.table')}>
            <Select value={table} onValueChange={setTable}>
              <SelectTrigger className="w-80">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(['runs', 'questions', 'characteristics'] as const).map((x) => (
                  <SelectItem key={x} value={x}>
                    {t(`exports.table.${x}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FieldRow>
          <FieldRow label={t('exports.format')}>
            <Select value={format} onValueChange={setFormat}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">CSV</SelectItem>
                <SelectItem value="json">JSON</SelectItem>
                <SelectItem value="parquet">Parquet</SelectItem>
              </SelectContent>
            </Select>
          </FieldRow>
          <Button onClick={() => void run()} disabled={busy}>
            {busy ? <LoaderCircle className="animate-spin" /> : <Download />}
            {t('exports.generate')}
          </Button>
        </div>
      </section>
      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">{t('exports.registered')}</h3>
        <DataTable
          columns={columns}
          rows={[...exports].reverse().filter((e) => e.kind !== 'run_artifact')}
          rowKey={(r) => String(r.id)}
          empty={<EmptyState title={t('exports.none')} />}
        />
      </section>
    </div>
  )
}

export default function ReportsPage(): React.JSX.Element {
  const t = usePageT(dict)
  const runbooks = useApiData<RunbookSummary[]>(useCallback(() => api.experiments.list(), []))
  const exports = useApiData<ExportRow[]>(useCallback(() => api.reports.list(), []))
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
            <Tabs defaultValue="report" className="gap-4">
              <TabsList>
                <TabsTrigger value="report">{t('tabs.report')}</TabsTrigger>
                <TabsTrigger value="figures">{t('tabs.figures')}</TabsTrigger>
                <TabsTrigger value="tables">{t('tabs.tables')}</TabsTrigger>
                <TabsTrigger value="exports">{t('tabs.exports')}</TabsTrigger>
              </TabsList>
              <TabsContent value="report">
                <ReportTab t={t} ids={ids} onDone={exports.reload} />
              </TabsContent>
              <TabsContent value="figures">
                <FiguresTab t={t} ids={ids} />
              </TabsContent>
              <TabsContent value="tables">
                <TablesTab t={t} ids={ids} />
              </TabsContent>
              <TabsContent value="exports">
                <ExportsTab t={t} ids={ids} exports={exports.data ?? []} onDone={exports.reload} />
              </TabsContent>
            </Tabs>
          )}
        </div>
      </div>
    </div>
  )
}
