import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider } from '@/components/theme-provider'
import { LanguageProvider } from '@/components/language-provider'
import { BackendStatusProvider } from '@/components/backend-status-provider'
import { TechniqueTitlesProvider } from '@/components/technique-titles-provider'
import { AppLayout } from '@/components/app-layout'
import { DEFAULT_ROUTE } from '@/lib/routes'
import CorpusPage from '@/pages/corpus'
import QuestionsPage from '@/pages/questions'
import TechniquesPage from '@/pages/techniques'
import ExperimentsPage from '@/pages/experiments'
import AnalysisPage from '@/pages/analysis'
import ReportsPage from '@/pages/reports'
import ReferencesPage from '@/pages/references'
import SettingsPage from '@/pages/settings'
import NotFoundPage from '@/pages/not-found-page'

export default function App(): React.JSX.Element {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <BackendStatusProvider>
          <TechniqueTitlesProvider>
            <TooltipProvider delayDuration={300}>
              <HashRouter>
                <Routes>
                  <Route element={<AppLayout />}>
                    <Route index element={<Navigate to={`/${DEFAULT_ROUTE}`} replace />} />
                    <Route path="corpus" element={<CorpusPage />} />
                    <Route path="questions" element={<QuestionsPage />} />
                    <Route path="techniques" element={<TechniquesPage />} />
                    <Route path="experiments" element={<ExperimentsPage />} />
                    <Route path="analysis" element={<AnalysisPage />} />
                    <Route path="reports" element={<ReportsPage />} />
                    <Route path="references" element={<ReferencesPage />} />
                    <Route path="settings" element={<SettingsPage />} />
                    <Route path="*" element={<NotFoundPage />} />
                  </Route>
                </Routes>
              </HashRouter>
              <Toaster richColors closeButton />
            </TooltipProvider>
          </TechniqueTitlesProvider>
        </BackendStatusProvider>
      </LanguageProvider>
    </ThemeProvider>
  )
}
