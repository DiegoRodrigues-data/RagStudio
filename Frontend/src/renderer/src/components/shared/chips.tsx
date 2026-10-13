import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ChipOption<T extends string> {
  value: T
  label?: string
  hint?: string
  /** Shown but not selectable (for example, a missing optional package explained in `hint`). */
  disabled?: boolean
}

/** Multi-select as toggle chips. `min` keeps at least that many selected. */
export function ToggleChips<T extends string>({
  options,
  value,
  onChange,
  min = 0,
  className
}: {
  options: ChipOption<T>[]
  value: T[]
  onChange: (next: T[]) => void
  min?: number
  className?: string
}): React.JSX.Element {
  const toggle = (v: T): void => {
    if (value.includes(v)) {
      if (value.length > min) onChange(value.filter((x) => x !== v))
    } else {
      onChange(options.map((o) => o.value).filter((o) => o === v || value.includes(o)))
    }
  }
  return (
    <div className={cn('flex flex-wrap gap-1.5', className)}>
      {options.map((o) => {
        const on = value.includes(o.value)
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            title={o.hint}
            disabled={o.disabled && !on}
            onClick={() => toggle(o.value)}
            className={cn(
              'inline-flex h-7 items-center gap-1 rounded-md border px-2 text-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:border-dashed disabled:opacity-50 disabled:hover:bg-background disabled:hover:text-muted-foreground',
              o.disabled && on && 'border-destructive bg-destructive text-white',
              o.disabled && on
                ? ''
                : on
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            {on && <Check className="size-3" />}
            {o.label ?? o.value}
          </button>
        )
      })}
    </div>
  )
}
