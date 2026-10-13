import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  LANGUAGES,
  LanguageContext,
  readStoredLanguage,
  storeLanguage,
  translate,
  type Language,
  type TranslationKey
} from '@/lib/i18n'

export function LanguageProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [language, setLanguageState] = useState<Language>(readStoredLanguage)

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const setLanguage = useCallback((lang: Language) => {
    storeLanguage(lang)
    setLanguageState(lang)
  }, [])

  const toggleLanguage = useCallback(() => {
    setLanguageState((prev) => {
      const next = LANGUAGES[(LANGUAGES.indexOf(prev) + 1) % LANGUAGES.length]
      storeLanguage(next)
      return next
    })
  }, [])

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      toggleLanguage,
      t: (key: TranslationKey, vars?: Record<string, string | number>) =>
        translate(language, key, vars)
    }),
    [language, setLanguage, toggleLanguage]
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}
