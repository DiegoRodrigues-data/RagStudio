import { useCallback, useState } from 'react'
import { Hammer, LoaderCircle, Search, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { DataTable, type DataTableColumn } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { fmtDate, shortHash } from '@/components/shared/exp-format'
import { FieldRow } from '@/components/shared/field-row'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import { useLanguage } from '@/hooks/use-t'
import { useStream } from '@/hooks/use-stream'
import { useStreamDone } from '@/hooks/use-stream-done'
import { chunkingLabel } from '@/lib/format'
import type { IndexRow, ProgressEvent, SearchHit } from '@/lib/types'
import { cn } from '@/lib/utils'
import type { CorpusKey } from './i18n'

const STRATEGIES = [
  'fixed',
  'recursive',
  'sentence',
  'semantic',
  'markdown_headers',
  'parent_child'
]
const MODES = ['dense', 'bm25', 'hybrid', 'rrf', 'mmr']

export function IndicesTab({
  t,
  corpus,
  splits
}: {
  t: PageT<CorpusKey>
  corpus: string
  splits: string[]
}): React.JSX.Element {
  const { language, t: gt } = useLanguage()
  const indices = useApiData<IndexRow[]>(useCallback(() => api.index.list(corpus), [corpus]))
  const [selected, setSelected] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<IndexRow | null>(null)

  // ---- build form
  const [strategy, setStrategy] = useState('fixed')
  const [size, setSize] = useState('1000')
  const [overlap, setOverlap] = useState('150')
  const [parentSize, setParentSize] = useState('1500')
  const [model, setModel] = useState('')
  const [split, setSplit] = useState('all')
  const [enrich, setEnrich] = useState(false)
  const build = useStream<ProgressEvent>()

  useStreamDone(build, (done) => {
    if (done.result?.ok) {
      const data = done.result.data as { reused?: boolean; index_hash?: string }
      toast.success(data.reused ? t('idx.reused') : t('idx.built'))
      if (data.index_hash) setSelected(data.index_hash)
      indices.reload()
    } else {
      toast.error(done.result && !done.result.ok ? done.result.error : (done.error ?? 'error'))
    }
  })

  const startBuild = (): void => {
    const chunking: Record<string, unknown> = {
      strategy,
      size: Number(size) || 1000,
      overlap: Number(overlap) || 0
    }
    if (strategy === 'parent_child') chunking.parent_size = Number(parentSize) || 1500
    void build.startWith((id) =>
      api.index.build(id, {
        corpus,
        chunking,
        embeddingModel: model.trim() || undefined,
        split: split === 'all' ? undefined : split,
        enrich: enrich ? 'contextual' : undefined
      })
    )
  }

  const last = build.lastEvent?.progress
  const pct =
    last && typeof last.done === 'number' && typeof last.total === 'number' && last.total > 0
      ? (last.done / last.total) * 100
      : build.running
        ? 5
        : 0

  // ---- search tester
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('dense')
  const [k, setK] = useState('5')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [searching, setSearching] = useState(false)

  const search = async (): Promise<void> => {
    if (!selected || !query.trim()) return
    setSearching(true)
    const res = await api.index.search(selected, query.trim(), mode, Number(k) || 5)
    setSearching(false)
    if (!res.ok) return void toast.error(res.error)
    setHits(res.data)
  }

  const remove = async (): Promise<void> => {
    if (!deleting) return
    const res = await api.index.delete(deleting.index_hash)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('idx.deleted'))
    if (selected === deleting.index_hash) setSelected(null)
    indices.reload()
  }

  const columns: DataTableColumn<IndexRow>[] = [
    {
      id: 'hash',
      header: t('idx.hash'),
      cell: (r) => <span className="font-mono text-xs">{shortHash(r.index_hash, 10)}</span>
    },
    {
      id: 'chunking',
      header: t('idx.chunking'),
      cell: (r) => <span className="font-mono text-xs">{chunkingLabel(r.chunking)}</span>
    },
    {
      id: 'embedding',
      header: t('idx.embedding'),
      cell: (r) => <span className="font-mono text-xs">{r.embedding_model}</span>
    },
    {
      id: 'extras',
      header: t('idx.store'),
      cell: (r) => (
        <span className="flex gap-1">
          <Badge variant="outline">{r.store}</Badge>
          {r.split && <Badge variant="secondary">{r.split}</Badge>}
          {r.enrich && <Badge variant="secondary">{r.enrich}</Badge>}
        </span>
      )
    },
    {
      id: 'chunks',
      header: t('idx.chunks'),
      className: 'text-right font-mono tabular-nums',
      headerClassName: 'text-right',
      cell: (r) => r.chunks.toLocaleString()
    },
    {
      id: 'dim',
      header: t('idx.dim'),
      className: 'text-right font-mono tabular-nums',
      headerClassName: 'text-right',
      cell: (r) => r.dim
    },
    {
      id: 'created',
      header: t('idx.created'),
      cell: (r) => (
        <span className="text-xs whitespace-nowrap">{fmtDate(r.created_at, language)}</span>
      )
    },
    {
      id: 'actions',
      header: '',
      className: 'w-10',
      cell: (r) => (
        <Button
          variant="ghost"
          size="icon-xs"
          aria-label={t('idx.delete')}
          onClick={(e) => {
            e.stopPropagation()
            setDeleting(r)
          }}
        >
          <Trash2 />
        </Button>
      )
    }
  ]

  return (
    <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="flex min-w-0 flex-col gap-4">
        <section className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">{t('idx.title')}</h3>
          <ErrorAlert
            title={t('common.errorTitle')}
            message={indices.error}
            retryLabel={gt('common.retry')}
            onRetry={indices.reload}
          />
          <DataTable
            columns={columns}
            rows={(indices.data ?? []).map((r) => ({ ...r }))}
            rowKey={(r) => r.index_hash}
            loading={indices.loading && !indices.data}
            onRowClick={(r) => setSelected(r.index_hash)}
            selected={new Set(selected ? [selected] : [])}
            empty={<EmptyState title={t('idx.empty')} description={t('idx.emptyHint')} />}
          />
        </section>

        <section className="flex flex-col gap-2 rounded-lg border bg-card p-4">
          <div>
            <h3 className="text-sm font-semibold">{t('idx.search')}</h3>
            <p className="text-xs text-muted-foreground">
              {selected ? `${t('idx.searchHint')} · ${shortHash(selected, 10)}` : t('idx.pick')}
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <FieldRow label={t('idx.query')} className="min-w-64 flex-1">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void search()}
                disabled={!selected}
              />
            </FieldRow>
            <FieldRow label={t('idx.mode')}>
              <Select value={mode} onValueChange={setMode}>
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MODES.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldRow>
            <FieldRow label="k">
              <Input value={k} onChange={(e) => setK(e.target.value)} className="w-16 font-mono" />
            </FieldRow>
            <Button
              onClick={() => void search()}
              disabled={!selected || !query.trim() || searching}
            >
              {searching ? <LoaderCircle className="animate-spin" /> : <Search />}
              {t('idx.run')}
            </Button>
          </div>
          {hits && hits.length === 0 && (
            <p className="text-xs text-muted-foreground">{t('idx.noHits')}</p>
          )}
          {hits && hits.length > 0 && (
            <ol className="flex flex-col gap-2">
              {hits.map((h) => (
                <li key={h.chunk_id} className="rounded-md border p-2">
                  <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                    <Badge variant="secondary">#{h.rank}</Badge>
                    <span className="font-mono">{h.chunk_id}</span>
                    <span className="font-mono">score {h.score.toFixed(4)}</span>
                    <span className="font-mono">
                      [{h.char_start}:{h.char_end}]
                    </span>
                    <Badge variant="outline">{h.source}</Badge>
                  </div>
                  <p className="text-xs leading-relaxed whitespace-pre-wrap">{h.text}</p>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <section className="flex flex-col gap-3 rounded-lg border bg-card p-4">
        <h3 className="text-sm font-semibold">{t('idx.build')}</h3>
        <FieldRow label={t('idx.strategy')}>
          <Select value={strategy} onValueChange={setStrategy}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STRATEGIES.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldRow>
        <div
          className={cn('grid gap-2', strategy === 'parent_child' ? 'grid-cols-3' : 'grid-cols-2')}
        >
          <FieldRow label={t('idx.size')}>
            <Input value={size} onChange={(e) => setSize(e.target.value)} className="font-mono" />
          </FieldRow>
          <FieldRow label={t('idx.overlap')}>
            <Input
              value={overlap}
              onChange={(e) => setOverlap(e.target.value)}
              className="font-mono"
            />
          </FieldRow>
          {strategy === 'parent_child' && (
            <FieldRow label={t('idx.parentSize')}>
              <Input
                value={parentSize}
                onChange={(e) => setParentSize(e.target.value)}
                className="font-mono"
              />
            </FieldRow>
          )}
        </div>
        <FieldRow label={t('idx.model')} help={t('idx.modelHint')}>
          <Input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="font-mono text-xs"
          />
        </FieldRow>
        <FieldRow label={t('idx.split')}>
          <Select value={split} onValueChange={setSplit}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('idx.allDocs')}</SelectItem>
              {splits.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldRow>
        <label className="flex items-start gap-2 text-xs">
          <Switch checked={enrich} onCheckedChange={setEnrich} />
          <span>
            <span className="font-medium">{t('idx.enrich')}</span>
            <span className="block text-muted-foreground">{t('idx.enrichHint')}</span>
          </span>
        </label>
        <Button onClick={startBuild} disabled={build.running}>
          {build.running ? <LoaderCircle className="animate-spin" /> : <Hammer />}
          {build.running ? t('idx.building') : t('idx.build')}
        </Button>
        {(build.running || build.done) && (
          <div className="flex flex-col gap-1">
            <Progress value={build.done ? 100 : pct} />
            <span className="font-mono text-[11px] text-muted-foreground">
              {last
                ? `${last.event}${typeof last.done === 'number' ? ` ${last.done}/${last.total}` : ''}`
                : '…'}
            </span>
          </div>
        )}
      </section>

      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={t('idx.delete')}
        description={
          deleting
            ? `${shortHash(deleting.index_hash, 16)} · ${chunkingLabel(deleting.chunking)}`
            : ''
        }
        confirmLabel={gt('common.delete')}
        cancelLabel={gt('common.cancel')}
        destructive
        onConfirm={remove}
      />
    </div>
  )
}
