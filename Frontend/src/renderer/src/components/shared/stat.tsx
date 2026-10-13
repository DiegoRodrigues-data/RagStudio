import { cn } from '@/lib/utils'

/** Small labelled figure used in summaries and monitors. */
export function Stat({
  label,
  value,
  hint,
  mono = false,
  className
}: {
  label: string
  value: React.ReactNode
  hint?: string
  mono?: boolean
  className?: string
}): React.JSX.Element {
  return (
    <div className={cn('min-w-0 rounded-md border bg-card p-2.5', className)}>
      <div className="truncate text-[11px] text-muted-foreground">{label}</div>
      <div
        className={cn('truncate text-sm font-semibold', mono && 'font-mono')}
        title={typeof value === 'string' ? value : undefined}
      >
        {value}
      </div>
      {hint && <div className="truncate text-[11px] text-muted-foreground">{hint}</div>}
    </div>
  )
}
