import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

/** Label + control + optional help text, stacked. */
export function FieldRow({
  label,
  htmlFor,
  help,
  error,
  children,
  className
}: {
  label: string
  htmlFor?: string
  help?: string
  error?: string | null
  children: React.ReactNode
  className?: string
}): React.JSX.Element {
  return (
    <div className={cn('flex min-w-0 flex-col gap-1', className)}>
      <Label htmlFor={htmlFor} className="text-xs">
        {label}
      </Label>
      {children}
      {error ? (
        <p className="text-[11px] text-destructive">{error}</p>
      ) : (
        help && <p className="text-[11px] text-muted-foreground">{help}</p>
      )}
    </div>
  )
}
