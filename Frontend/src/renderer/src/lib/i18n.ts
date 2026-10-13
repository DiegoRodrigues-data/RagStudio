import { createContext } from 'react'
import ptBR from '@/locales/pt-BR.json'
import en from '@/locales/en.json'

export type Language = 'pt-BR' | 'en'
export type TranslationKey = keyof typeof ptBR

export const LANGUAGES: Language[] = ['pt-BR', 'en']
export const DEFAULT_LANGUAGE: Language = 'pt-BR'
export const LANGUAGE_STORAGE_KEY = 'ragstudio.language'

// `en` must contain exactly the same keys as `pt-BR` (checked at compile time).
const enChecked: Record<TranslationKey, string> = en

export const dictionaries: Record<Language, Record<TranslationKey, string>> = {
  'pt-BR': ptBR,
  en: enChecked
}

export function isLanguage(value: unknown): value is Language {
  return typeof value === 'string' && (LANGUAGES as string[]).includes(value)
}

export function readStoredLanguage(): Language {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    if (isLanguage(stored)) return stored
  } catch {
    /* localStorage unavailable */
  }
  return DEFAULT_LANGUAGE
}

export function storeLanguage(lang: Language): void {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lang)
  } catch {
    /* ignore */
  }
}

export type TFunction = (key: TranslationKey, vars?: Record<string, string | number>) => string

export function translate(
  lang: Language,
  key: TranslationKey,
  vars?: Record<string, string | number>
): string {
  let text: string = dictionaries[lang][key] ?? dictionaries[DEFAULT_LANGUAGE][key] ?? key
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replaceAll(`{${k}}`, String(v))
    }
  }
  return text
}

export interface LanguageContextValue {
  language: Language
  setLanguage: (lang: Language) => void
  toggleLanguage: () => void
  t: TFunction
}

export const LanguageContext = createContext<LanguageContextValue | null>(null)
