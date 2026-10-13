import {
  BookOpen,
  ChartColumn,
  CircleQuestionMark,
  FileText,
  FlaskConical,
  Layers,
  Microscope,
  Settings,
  type LucideIcon
} from 'lucide-react'
import type { TranslationKey } from './i18n'

export interface AppRoute {
  /** Route path (without leading slash). */
  path: string
  navKey: TranslationKey
  titleKey: TranslationKey
  descriptionKey: TranslationKey
  icon: LucideIcon
  group: 'workspace' | 'analysis' | 'help' | 'system'
}

/** Navigation entries, in display order (they follow the flow document -> processing -> result). */
export const APP_ROUTES: AppRoute[] = [
  {
    path: 'corpus',
    navKey: 'nav.corpus',
    titleKey: 'page.corpus.title',
    descriptionKey: 'page.corpus.description',
    icon: FileText,
    group: 'workspace'
  },
  {
    path: 'questions',
    navKey: 'nav.questions',
    titleKey: 'page.questions.title',
    descriptionKey: 'page.questions.description',
    icon: CircleQuestionMark,
    group: 'workspace'
  },
  {
    path: 'techniques',
    navKey: 'nav.techniques',
    titleKey: 'page.techniques.title',
    descriptionKey: 'page.techniques.description',
    icon: Layers,
    group: 'workspace'
  },
  {
    path: 'experiments',
    navKey: 'nav.experiments',
    titleKey: 'page.experiments.title',
    descriptionKey: 'page.experiments.description',
    icon: FlaskConical,
    group: 'analysis'
  },
  {
    path: 'analysis',
    navKey: 'nav.analysis',
    titleKey: 'page.analysis.title',
    descriptionKey: 'page.analysis.description',
    icon: Microscope,
    group: 'analysis'
  },
  {
    path: 'reports',
    navKey: 'nav.reports',
    titleKey: 'page.reports.title',
    descriptionKey: 'page.reports.description',
    icon: ChartColumn,
    group: 'analysis'
  },
  {
    path: 'references',
    navKey: 'nav.references',
    titleKey: 'page.references.title',
    descriptionKey: 'page.references.description',
    icon: BookOpen,
    group: 'help'
  },
  {
    path: 'settings',
    navKey: 'nav.settings',
    titleKey: 'page.settings.title',
    descriptionKey: 'page.settings.description',
    icon: Settings,
    group: 'system'
  }
]

export const DEFAULT_ROUTE = APP_ROUTES[0].path

export const ROUTE_GROUPS: { id: AppRoute['group']; labelKey: TranslationKey }[] = [
  { id: 'workspace', labelKey: 'nav.group.workspace' },
  { id: 'analysis', labelKey: 'nav.group.analysis' },
  { id: 'help', labelKey: 'nav.group.help' },
  { id: 'system', labelKey: 'nav.group.system' }
]

export function findRoute(pathname: string): AppRoute | undefined {
  const first = pathname.replace(/^\/+/, '').split('/')[0]
  return APP_ROUTES.find((r) => r.path === first)
}
