import { useContext } from 'react'
import { LanguageContext, type LanguageContextValue, type TFunction } from '@/lib/i18n'

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used inside <LanguageProvider>')
  return ctx
}

/** Tiny i18n hook: `const t = useT(); t('nav.documents')`. */
export function useT(): TFunction {
  return useLanguage().t
}
