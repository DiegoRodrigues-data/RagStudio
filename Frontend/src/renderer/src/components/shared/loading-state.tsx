import { LoaderCircle } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface LoadingStateProps {
  /** Number of skeleton rows (ignored when `label` is given). */
  rows?: number
  /** When set, renders a compact spinner + text instead of skeleton rows. */
  label?: string
  className?: string
}

/** Loading placeholder: skeleton rows, or a spinner with a label. */
export function LoadingState({ rows = 4, label, className }: LoadingStateProps): React.JSX.Element {
  if (label) {
    return (
      <div
        className={cn('flex items-center gap-2 py-4 text-sm text-muted-foreground', className)}
        aria-busy
      >
        <LoaderCircle className="size-4 animate-spin" aria-hidden />
        <span>{label}</span>
      </div>
    )
  }
  return (
    <div className={cn('flex flex-col gap-2', className)} aria-busy>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  )
}
