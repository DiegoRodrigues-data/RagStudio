import { Badge } from '@/components/ui/badge'
import type { TechniqueStatus } from '@/lib/types'

/** Status of a technique: implemented is the plain default; anything else is called out. */
export function TechniqueStatusBadge({
  status,
  label
}: {
  status: TechniqueStatus | string
  label: string
}): React.JSX.Element {
  if (status === 'implemented') return <Badge variant="secondary">{label}</Badge>
  return (
    <Badge variant="outline" className="border-amber-500/60 text-amber-700 dark:text-amber-400">
      {label}
    </Badge>
  )
}
