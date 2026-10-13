import { useLocation } from 'react-router-dom'
import { useT } from '@/hooks/use-t'
import { findRoute } from '@/lib/routes'

/** Title + description of the current route, with the page actions on the right. */
export function PageHeader({ children }: { children?: React.ReactNode }): React.JSX.Element {
  const t = useT()
  const route = findRoute(useLocation().pathname)
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-2xl font-semibold tracking-tight">{route ? t(route.titleKey) : ''}</h2>
        <p className="text-sm text-muted-foreground">{route ? t(route.descriptionKey) : ''}</p>
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}
