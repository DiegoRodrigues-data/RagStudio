import { CircleCheck, CircleX, LoaderCircle } from 'lucide-react'
import { SidebarMenuButton } from '@/components/ui/sidebar'
import { useBackendStatus } from '@/hooks/use-backend-status'
import { useT } from '@/hooks/use-t'
import { cn } from '@/lib/utils'

/** Compact "Backend: OK / unavailable" indicator for the sidebar footer. Click to re-check. */
export function BackendStatusWidget(): React.JSX.Element {
  const t = useT()
  const { state, paths, error, refresh } = useBackendStatus()

  const Icon = state === 'checking' ? LoaderCircle : state === 'ok' ? CircleCheck : CircleX
  const label =
    state === 'checking'
      ? t('backend.checking')
      : state === 'ok'
        ? t('backend.ok')
        : t('backend.unavailable')

  const tooltip = (
    <div className="space-y-1 text-xs">
      <div>
        {t('backend.status')}: {label}
      </div>
      <div>
        <span className="font-medium">{t('backend.python')}:</span>{' '}
        <span className="font-mono break-all">{paths?.python ?? '…'}</span>
      </div>
      {error && <div className="break-words">{error}</div>}
    </div>
  )

  return (
    <SidebarMenuButton
      onClick={() => void refresh()}
      aria-label={`${t('backend.status')}: ${label}`}
      tooltip={{ children: tooltip, side: 'right', hidden: false, className: 'max-w-sm' }}
    >
      <Icon
        className={cn(
          'size-4 shrink-0',
          state === 'checking' && 'text-muted-foreground animate-spin',
          state === 'ok' && 'text-emerald-600 dark:text-emerald-400',
          state === 'error' && 'text-destructive'
        )}
      />
      <span className="truncate text-xs">
        {t('backend.status')}: {label}
      </span>
    </SidebarMenuButton>
  )
}
