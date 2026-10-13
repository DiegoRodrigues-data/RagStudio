import { FlaskConical } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useT } from '@/hooks/use-t'

/** Shown wherever numbers produced by the mock provider are displayed. */
export function MockBadge({ provider }: { provider: unknown }): React.JSX.Element | null {
  const t = useT()
  if (provider !== 'mock') return null
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant="outline" className="border-amber-500/60 text-amber-700 dark:text-amber-400">
          <FlaskConical /> {t('mock.badge')}
        </Badge>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{t('mock.hint')}</TooltipContent>
    </Tooltip>
  )
}
