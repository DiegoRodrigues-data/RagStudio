import { useCallback } from 'react'
import { useT } from '@/hooks/use-t'
import type { TranslationKey } from '@/lib/i18n'

const KNOWN = new Set(['pending', 'running', 'completed', 'failed', 'cancelled', 'budget_exceeded'])

/** Translated label for a runbook/run status (falls back to the raw value). */
export function useStatusLabel(): (status: string) => string {
  const t = useT()
  return useCallback(
    (status: string) => (KNOWN.has(status) ? t(`status.${status}` as TranslationKey) : status),
    [t]
  )
}
