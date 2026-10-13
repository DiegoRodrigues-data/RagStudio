import { NavLink, useLocation } from 'react-router-dom'
import { Workflow } from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail
} from '@/components/ui/sidebar'
import { BackendStatusWidget } from '@/components/backend-status-widget'
import { useT } from '@/hooks/use-t'
import { APP_ROUTES, ROUTE_GROUPS, findRoute } from '@/lib/routes'

export function AppSidebar(): React.JSX.Element {
  const t = useT()
  const location = useLocation()
  const active = findRoute(location.pathname)

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild tooltip={t('app.name')}>
              <NavLink to="/">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Workflow className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">{t('app.name')}</span>
                  <span className="truncate text-xs text-muted-foreground">{t('app.tagline')}</span>
                </div>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {ROUTE_GROUPS.map((group) => {
          const routes = APP_ROUTES.filter((r) => r.group === group.id)
          if (routes.length === 0) return null
          return (
            <SidebarGroup key={group.id}>
              <SidebarGroupLabel>{t(group.labelKey)}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {routes.map((route) => (
                    <SidebarMenuItem key={route.path}>
                      <SidebarMenuButton
                        asChild
                        isActive={active?.path === route.path}
                        tooltip={t(route.navKey)}
                      >
                        <NavLink to={`/${route.path}`}>
                          <route.icon />
                          <span>{t(route.navKey)}</span>
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <BackendStatusWidget />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
