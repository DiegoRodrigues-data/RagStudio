import { useLocation } from 'react-router-dom'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { ThemeToggle } from '@/components/theme-toggle'
import { LanguageToggle } from '@/components/language-toggle'
import { useT } from '@/hooks/use-t'
import { findRoute } from '@/lib/routes'

export function TopBar(): React.JSX.Element {
  const t = useT()
  const location = useLocation()
  const route = findRoute(location.pathname)
  const title = route ? t(route.titleKey) : t('page.notFound.title')

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
      <SidebarTrigger className="-ml-1" aria-label={t('nav.toggleSidebar')} />
      <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
      <h1 className="truncate text-base font-semibold">{title}</h1>
      <div className="ml-auto flex items-center gap-1">
        <LanguageToggle />
        <ThemeToggle />
      </div>
    </header>
  )
}
