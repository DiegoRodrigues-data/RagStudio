import { useCallback, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { api } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { ToggleChips } from '@/components/shared/chips'
import { DataTable, type DataTableColumn } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorAlert } from '@/components/shared/error-alert'
import { PageHeader } from '@/components/shared/page-header'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import { STAGES, axisKey, stageKey } from '@/lib/stages'
import type { TechniqueInfo } from '@/lib/types'
import { dict, type TechKey } from './i18n'
import { TechniqueStatusBadge } from './status-badge'

export default function TechniquesPage(): React.JSX.Element {
  const t = usePageT(dict)
  const gt = useT()
  const list = useApiData<TechniqueInfo[]>(useCallback(() => api.techniques.list(), []))
  const [filter, setFilter] = useState('')
  const [statuses, setStatuses] = useState<string[]>([])
  const [stages, setStages] = useState<string[]>([])

  const all = [...(list.data ?? [])].sort(
    (a, b) =>
      (STAGES as readonly string[]).indexOf(a.stage) -
        (STAGES as readonly string[]).indexOf(b.stage) ||
      (a.title || a.name).localeCompare(b.title || b.name)
  )
  const present = [...new Set(all.map((x) => x.status))]
  const needle = filter.trim().toLowerCase()
  const rows = all.filter(
    (x) =>
      (statuses.length === 0 || statuses.includes(x.status)) &&
      (stages.length === 0 || stages.includes(x.stage)) &&
      (!needle ||
        `${x.name} ${x.title} ${x.family} ${x.description}`.toLowerCase().includes(needle))
  )

  const columns: DataTableColumn<TechniqueInfo>[] = [
    {
      id: 'name',
      header: t('col.name'),
      cell: (r) => (
        <div className="flex flex-col">
          <span className="text-sm font-medium">{r.title || r.name}</span>
          <span className="font-mono text-[11px] text-muted-foreground">
            {r.name} · v{r.version}
          </span>
        </div>
      )
    },
    {
      id: 'stage',
      header: t('col.stage'),
      cell: (r) => (
        <div className="flex flex-col">
          <span className="text-xs font-medium">{gt(stageKey(r.stage))}</span>
          <span className="text-[11px] text-muted-foreground">{r.family}</span>
        </div>
      )
    },
    {
      id: 'axes',
      header: t('col.axes'),
      className: 'max-w-48 whitespace-normal',
      cell: (r) => {
        const needs = r.requires.filter((x) => x.startsWith('index:') && x !== 'index:aux')
        if (r.ignores.length === 0 && needs.length === 0)
          return <span className="text-xs text-muted-foreground">{t('axes.all')}</span>
        return (
          <div className="flex flex-col gap-0.5 text-[11px]">
            {r.ignores.length > 0 && (
              <span>
                {t('axes.ignores', { axes: r.ignores.map((a) => gt(axisKey(a))).join(', ') })}
              </span>
            )}
            {needs.map((x) => (
              <span key={x} className="text-amber-700 dark:text-amber-400">
                {t('axes.needs', { index: x.slice(6) })}
              </span>
            ))}
          </div>
        )
      }
    },
    {
      id: 'status',
      header: t('col.status'),
      cell: (r) => (
        <TechniqueStatusBadge status={r.status} label={t(`status.${r.status}` as TechKey)} />
      )
    },
    {
      id: 'description',
      header: t('col.description'),
      className: 'max-w-md whitespace-normal text-xs leading-relaxed',
      cell: (r) => r.description
    },
    {
      id: 'params',
      header: t('col.params'),
      className: 'max-w-sm whitespace-normal',
      cell: (r) => {
        const entries = Object.entries(r.params)
        if (entries.length === 0)
          return <span className="text-xs text-muted-foreground">{t('noParams')}</span>
        return (
          <div className="flex flex-wrap gap-1">
            {entries.map(([k, v]) => (
              <code key={k} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
                {k}={v === null ? '∅' : String(v)}
              </code>
            ))}
          </div>
        )
      }
    },
    {
      id: 'reference',
      header: t('col.reference'),
      cell: (r) =>
        r.reference ? (
          <a
            href={r.reference}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-primary underline-offset-4 hover:underline"
            title={r.reference}
          >
            <ExternalLink className="size-3" /> {new URL(r.reference).hostname.replace('www.', '')}
          </a>
        ) : (
          '–'
        )
    }
  ]

  return (
    <div className="flex flex-col gap-4">
      <PageHeader />
      <div className="flex flex-wrap items-center gap-3">
        <Input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={t('filter.placeholder')}
          className="h-8 max-w-sm"
        />
        <ToggleChips
          options={STAGES.filter((s) => all.some((x) => x.stage === s)).map((s) => ({
            value: s as string,
            label: gt(stageKey(s))
          }))}
          value={stages}
          onChange={setStages}
        />
        <ToggleChips
          options={present.map((s) => ({ value: s, label: t(`status.${s}` as TechKey) }))}
          value={statuses as typeof present}
          onChange={setStatuses}
        />
        {all.length > 0 && (
          <span className="text-xs text-muted-foreground">
            {t('summary', {
              n: all.length,
              impl: all.filter((x) => x.status === 'implemented').length,
              proto: all.filter((x) => x.status === 'prototype').length
            })}
          </span>
        )}
      </div>
      <ErrorAlert
        title={t('errorTitle')}
        message={list.error}
        retryLabel={gt('common.retry')}
        onRetry={list.reload}
      />
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.name}
        loading={list.loading && !list.data}
        empty={<EmptyState title={t('empty')} />}
      />
      <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
        <p>
          <TechniqueStatusBadge status="implemented" label={t('status.implemented')} />{' '}
          {t('legend.implemented')}
        </p>
        <p>
          <TechniqueStatusBadge status="prototype" label={t('status.prototype')} />{' '}
          {t('legend.prototype')}
        </p>
        <p>{t('legend.note')}</p>
      </div>
    </div>
  )
}
