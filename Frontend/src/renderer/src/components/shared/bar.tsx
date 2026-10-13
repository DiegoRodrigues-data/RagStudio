import { cn } from '@/lib/utils'

/**
 * One horizontal bar on a shared scale. A single series uses a single hue; the value is always
 * written next to the bar in ink, so identity never depends on color.
 */
export function Bar({
  label,
  value,
  max,
  text,
  hint,
  className
}: {
  label: string
  value: number | null
  max: number
  text: string
  hint?: string
  className?: string
}): React.JSX.Element {
  const pct = value === null || max <= 0 ? 0 : Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div
      className={cn(
        'grid grid-cols-[minmax(7rem,14rem)_minmax(0,1fr)_4.5rem] items-center gap-2',
        className
      )}
      title={hint}
    >
      <span className="truncate font-mono text-xs" title={label}>
        {label}
      </span>
      <span className="h-4 overflow-hidden rounded-sm bg-muted">
        {value !== null && (
          <span
            className="block h-full rounded-r-sm bg-(--series-1)"
            style={{ width: `${pct}%`, minWidth: value > 0 ? 2 : 0 }}
          />
        )}
      </span>
      <span className="text-right font-mono text-xs tabular-nums">{text}</span>
    </div>
  )
}
