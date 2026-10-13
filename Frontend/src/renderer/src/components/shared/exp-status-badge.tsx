import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type Variant = 'default' | 'secondary' | 'destructive' | 'outline'

function variantFor(status: string): Variant {
  switch (status) {
    case 'completed':
      return 'default'
    case 'running':
    case 'completed_with_errors':
    case 'paused':
      return 'secondary'
    case 'failed':
    case 'cancelled':
    case 'budget_exceeded':
      return 'destructive'
    default:
      return 'outline'
  }
}

/** Status pill for runbooks / runs. `label` is the translated text (defaults to the raw status). */
export function StatusBadge({
  status,
  label,
  className
}: {
  status: string
  label?: string
  className?: string
}): React.JSX.Element {
  return (
    <Badge variant={variantFor(status)} className={cn('capitalize', className)}>
      {status === 'running' && <span className="size-1.5 animate-pulse rounded-full bg-current" />}
      {label ?? status}
    </Badge>
  )
}
