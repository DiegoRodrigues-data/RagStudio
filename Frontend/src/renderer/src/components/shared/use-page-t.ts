import { useCallback } from 'react'
import { useLanguage } from '@/hooks/use-t'
import type { Language } from '@/lib/i18n'

/** Per-page dictionary: `{ 'pt-BR': {...}, en: {...} }` with the same keys in both languages. */
export type PageDict<K extends string> = Record<Language, Record<K, string>>

export type PageT<K extends string> = (key: K, vars?: Record<string, string | number>) => string

/**
 * Page-local translations. Keeps page strings next to the page instead of the global
 * locale files: `const t = usePageT(dict); t('import.title')`.
 */
export function usePageT<K extends string>(dict: PageDict<K>): PageT<K> {
  const { language } = useLanguage()
  return useCallback(
    (key: K, vars?: Record<string, string | number>): string => {
      let text: string = dict[language]?.[key] ?? dict['pt-BR'][key] ?? key
      if (vars) {
        for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, String(v))
      }
      return text
    },
    [dict, language]
  )
}
