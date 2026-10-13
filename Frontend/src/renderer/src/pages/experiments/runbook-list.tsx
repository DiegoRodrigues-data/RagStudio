import { useState } from 'react'
import { FlaskConical, MoreHorizontal, Play, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EmptyState } from '@/components/shared/empty-state'
import { fmtDate } from '@/components/shared/exp-format'
import { StatusBadge } from '@/components/shared/exp-status-badge'
import { LoadingState } from '@/components/shared/loading-state'
import { fmtMetric } from '@/components/shared/metrics'
import type { PageT } from '@/components/shared/use-page-t'
import { useStatusLabel } from '@/components/shared/use-status-label'
import { useLanguage } from '@/hooks/use-t'
import type { RunbookSummary } from '@/lib/types'
import { cn } from '@/lib/utils'
import { DeleteRunbookDialog } from './delete-dialog'
import type { ExpKey } from './i18n'

interface Props {
  t: PageT<ExpKey>
  runbooks: RunbookSummary[] | null
  loading: boolean
  error: string | null
  selectedId: string | null
  onSelect: (id: string) => void
  onReload: () => void
  onDeleted: (id: string) => void
  onRun: (id: string) => void
  onNew: () => void
  /** Id of the runbook currently executing (disables run / delete). */
  runningId: string | null
}

export function RunbookList({
  t,
  runbooks,
  loading,
  error,
  selectedId,
  onSelect,
  onReload,
  onDeleted,
  onRun,
  onNew,
  runningId
}: Props): React.JSX.Element {
  const { language } = useLanguage()
  const statusLabel = useStatusLabel()
  const [deleting, setDeleting] = useState<RunbookSummary | null>(null)

  const verify = async (rb: RunbookSummary): Promise<void> => {
    const res = await api.experiments.verify(rb.id)
    if (!res.ok) return void toast.error(res.error)
    if (res.data.ok) toast.success(t('list.verified', { n: Object.keys(res.data.runs).length }))
    else toast.error(t('list.broken'))
  }

  return (
    <div className="flex h-full flex-col rounded-lg border bg-card">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FlaskConical className="size-4" />
          {t('list.title')}
          {runbooks && <Badge variant="secondary">{runbooks.length}</Badge>}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon-xs" onClick={onReload} aria-label="refresh">
            <RefreshCw className={cn(loading && 'animate-spin')} />
          </Button>
          <Button variant="outline" size="xs" onClick={onNew}>
            {t('list.new')}
          </Button>
        </div>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="flex flex-col gap-1 p-2">
          {loading && !runbooks && <LoadingState label={t('common.loading')} />}
          {error && <div className="p-2 text-xs text-destructive">{error}</div>}
          {runbooks && runbooks.length === 0 && (
            <EmptyState title={t('list.empty')} className="border-0 p-6" />
          )}
          {[...(runbooks ?? [])].reverse().map((rb) => {
            const selected = rb.id === selectedId
            const busy = runningId === rb.id
            return (
              <div
                key={rb.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(rb.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') onSelect(rb.id)
                }}
                className={cn(
                  'group flex flex-col gap-1 rounded-md border px-2.5 py-2 text-left text-sm outline-none transition-colors',
                  selected ? 'border-primary/40 bg-muted' : 'border-transparent hover:bg-muted/60',
                  'focus-visible:ring-2 focus-visible:ring-ring/50'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium" title={rb.name}>
                      {rb.name}
                    </div>
                    <div className="truncate font-mono text-[11px] text-muted-foreground">
                      {rb.id}
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={(e) => e.stopPropagation()}
                        aria-label="actions"
                      >
                        <MoreHorizontal />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenuItem disabled={!!runningId} onClick={() => onRun(rb.id)}>
                        <Play /> {t('list.run')}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => void verify(rb)}>
                        <ShieldCheck /> {t('list.verify')}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        variant="destructive"
                        disabled={busy}
                        onClick={() => setDeleting(rb)}
                      >
                        <Trash2 /> {t('list.delete')}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <StatusBadge
                    status={busy ? 'running' : rb.status}
                    label={statusLabel(busy ? 'running' : rb.status)}
                  />
                  <span className="text-xs text-muted-foreground">
                    {t('list.runs', { done: rb.completed, total: rb.runs })}
                  </span>
                </div>
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>
                    {t('list.cost')}: {fmtMetric('cost_usd', rb.cost_usd)}
                  </span>
                  <span>{fmtDate(rb.created_at, language)}</span>
                </div>
              </div>
            )
          })}
        </div>
      </ScrollArea>
      {deleting && (
        <DeleteRunbookDialog
          t={t}
          runbook={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={onDeleted}
        />
      )}
    </div>
  )
}
