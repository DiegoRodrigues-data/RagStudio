import { useMemo, useState } from 'react'
import { LoaderCircle, Search, Shuffle } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/empty-state'
import { FieldRow } from '@/components/shared/field-row'
import type { PageT } from '@/components/shared/use-page-t'
import { cn } from '@/lib/utils'
import type { CorpusKey } from './i18n'

const NAMES = ['train', 'validation', 'test'] as const
type SplitName = (typeof NAMES)[number]

function pct(part: number, total: number): string {
  return total > 0 ? `${((part / total) * 100).toFixed(1)}%` : '–'
}

function SplitColumn({
  t,
  title,
  ids,
  chars,
  totalDocs,
  totalChars,
  needle,
  onOpen
}: {
  t: PageT<CorpusKey>
  title: string
  ids: string[]
  chars: Map<string, number>
  totalDocs: number
  totalChars: number
  needle: string
  onOpen: (docId: string) => void
}): React.JSX.Element {
  const sum = ids.reduce((acc, id) => acc + (chars.get(id) ?? 0), 0)
  const shown = needle ? ids.filter((id) => id.toLowerCase().includes(needle)) : ids
  const share = totalDocs > 0 ? (ids.length / totalDocs) * 100 : 0
  return (
    <section className="flex min-w-0 flex-col rounded-lg border bg-card">
      <header className="flex flex-col gap-1.5 border-b p-3">
        <div className="flex items-baseline justify-between gap-2">
          <h4 className="text-sm font-semibold">{title}</h4>
          <span className="font-mono text-sm font-semibold tabular-nums">{ids.length}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-sm bg-muted">
          <div className="h-full rounded-sm bg-(--series-1)" style={{ width: `${share}%` }} />
        </div>
        <div className="flex justify-between gap-2 text-[11px] text-muted-foreground">
          <span>{t('splits.shareDocs', { p: pct(ids.length, totalDocs) })}</span>
          <span className="font-mono tabular-nums">
            {t('splits.shareChars', { n: sum.toLocaleString(), p: pct(sum, totalChars) })}
          </span>
        </div>
      </header>
      <ul className="max-h-[max(14rem,calc(100svh-35rem))] overflow-y-auto p-1.5">
        {shown.length === 0 && (
          <li className="px-2 py-3 text-center text-xs text-muted-foreground">
            {t('splits.noMatch')}
          </li>
        )}
        {shown.map((id) => (
          <li key={id}>
            <button
              type="button"
              onClick={() => onOpen(id)}
              title={id}
              className="flex w-full items-center justify-between gap-3 rounded-sm px-2 py-1 text-left text-xs outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50"
            >
              <span className="truncate font-mono">{id}</span>
              <span className="shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                {(chars.get(id) ?? 0).toLocaleString()}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function SplitsTab({
  t,
  corpus,
  splits,
  documents,
  onChanged,
  onOpenDocument
}: {
  t: PageT<CorpusKey>
  corpus: string
  /** split -> document ids (empty object when none). */
  splits: Record<string, string[]>
  documents: { doc_id: string; chars: number }[]
  onChanged: () => void
  onOpenDocument: (docId: string) => void
}): React.JSX.Element {
  const [ratios, setRatios] = useState<Record<SplitName, string>>({
    train: '0.6',
    validation: '0.2',
    test: '0.2'
  })
  const [seed, setSeed] = useState('42')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('')

  const nums = {
    train: Number(ratios.train) || 0,
    validation: Number(ratios.validation) || 0,
    test: Number(ratios.test) || 0
  }
  const ratioSum = nums.train + nums.validation + nums.test

  const apply = async (): Promise<void> => {
    if (ratioSum <= 0) return setError(t('splits.ratioError'))
    setError(null)
    setBusy(true)
    const res = await api.corpus.split(corpus, { ...nums, seed: Number(seed) || 42 })
    setBusy(false)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('splits.done'))
    onChanged()
  }

  const chars = useMemo(() => new Map(documents.map((d) => [d.doc_id, d.chars])), [documents])
  const totalChars = documents.reduce((acc, d) => acc + d.chars, 0)
  const defined = NAMES.filter((n) => (splits[n] ?? []).length > 0)
  const assigned = new Set(defined.flatMap((n) => splits[n]))
  const unassigned = documents.map((d) => d.doc_id).filter((id) => !assigned.has(id))
  const needle = filter.trim().toLowerCase()
  const columns = defined.length + (defined.length > 0 && unassigned.length > 0 ? 1 : 0)

  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-3 rounded-lg border bg-card p-4">
        <div>
          <h3 className="text-sm font-semibold">{t('splits.title')}</h3>
          <p className="text-xs text-muted-foreground">{t('splits.hint')}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          {NAMES.map((n) => (
            <FieldRow
              key={n}
              label={t(`splits.${n}`)}
              className="w-36"
              help={
                ratioSum > 0
                  ? t('splits.expect', {
                      p: pct(nums[n], ratioSum),
                      n: Math.round((nums[n] / ratioSum) * documents.length)
                    })
                  : '–'
              }
            >
              <Input
                value={ratios[n]}
                inputMode="decimal"
                onChange={(e) => setRatios((r) => ({ ...r, [n]: e.target.value }))}
                className="font-mono"
              />
            </FieldRow>
          ))}
          <FieldRow label={t('splits.seed')} className="w-36" help={t('splits.seedHint')}>
            <Input value={seed} onChange={(e) => setSeed(e.target.value)} className="font-mono" />
          </FieldRow>
          <Button onClick={() => void apply()} disabled={busy} className="mb-[1.375rem]">
            {busy ? <LoaderCircle className="animate-spin" /> : <Shuffle />}
            {defined.length > 0 ? t('splits.redraw') : t('splits.apply')}
          </Button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
        {defined.length > 0 && (
          <p className="text-xs text-amber-700 dark:text-amber-400">{t('splits.redrawHint')}</p>
        )}
      </section>

      <section className="flex min-w-0 flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">
            {t('splits.current')}
            {defined.length > 0 && (
              <span className="ml-2 font-normal text-muted-foreground">
                {t('splits.total', {
                  n: documents.length,
                  c: totalChars.toLocaleString()
                })}
              </span>
            )}
          </h3>
          {defined.length > 0 && (
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder={t('splits.filter')}
                className="h-8 w-64 pl-7"
              />
            </div>
          )}
        </div>
        {defined.length === 0 ? (
          <EmptyState title={t('splits.none')} description={t('splits.noneHint')} />
        ) : (
          <div
            className={cn(
              'grid items-start gap-3',
              columns >= 4 ? 'md:grid-cols-2 xl:grid-cols-4' : 'md:grid-cols-3'
            )}
          >
            {defined.map((n) => (
              <SplitColumn
                key={n}
                t={t}
                title={t(`splits.${n}`)}
                ids={splits[n]}
                chars={chars}
                totalDocs={documents.length}
                totalChars={totalChars}
                needle={needle}
                onOpen={onOpenDocument}
              />
            ))}
            {unassigned.length > 0 && (
              <SplitColumn
                t={t}
                title={t('splits.unassigned')}
                ids={unassigned}
                chars={chars}
                totalDocs={documents.length}
                totalChars={totalChars}
                needle={needle}
                onOpen={onOpenDocument}
              />
            )}
          </div>
        )}
      </section>
    </div>
  )
}
