import { Check } from 'lucide-react'
import { StatusBadge } from '@/components/shared/exp-status-badge'
import { useStatusLabel } from '@/components/shared/use-status-label'
import type { RunbookSummary } from '@/lib/types'
import { cn } from '@/lib/utils'

/** Multi-select list of runbooks (only those with completed runs can be analysed). */
export function RunbookPicker({
  runbooks,
  value,
  onChange,
  emptyLabel,
  runsLabel
}: {
  runbooks: RunbookSummary[]
  value: string[]
  onChange: (ids: string[]) => void
  emptyLabel: string
  runsLabel: (done: number, total: number) => string
}): React.JSX.Element {
  const statusLabel = useStatusLabel()
  const usable = [...runbooks].reverse()
  if (usable.length === 0) return <p className="p-3 text-xs text-muted-foreground">{emptyLabel}</p>
  return (
    <ul className="flex flex-col gap-1">
      {usable.map((rb) => {
        const on = value.includes(rb.id)
        const disabled = rb.completed === 0
        return (
          <li key={rb.id}>
            <button
              type="button"
              disabled={disabled}
              aria-pressed={on}
              onClick={() => onChange(on ? value.filter((x) => x !== rb.id) : [...value, rb.id])}
              className={cn(
                'flex w-full items-start gap-2 rounded-md border px-2.5 py-2 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50',
                on ? 'border-primary/40 bg-muted' : 'border-transparent hover:bg-muted/60'
              )}
            >
              <span
                className={cn(
                  'mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border',
                  on ? 'border-primary bg-primary text-primary-foreground' : 'border-input'
                )}
              >
                {on && <Check className="size-3" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{rb.name}</span>
                <span className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                  <StatusBadge status={rb.status} label={statusLabel(rb.status)} />
                  {runsLabel(rb.completed, rb.runs)}
                </span>
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
