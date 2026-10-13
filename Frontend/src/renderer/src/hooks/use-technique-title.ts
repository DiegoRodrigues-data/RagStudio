import { useCallback, useContext } from 'react'
import { TechniqueTitlesContext } from '@/lib/technique-titles'

/** `const title = useTechniqueTitle(); title('corrective')` -> "Corrective RAG" (the identifier while loading). */
export function useTechniqueTitle(): (name: string | null | undefined) => string {
  const titles = useContext(TechniqueTitlesContext)
  return useCallback((name) => (name ? (titles[name] ?? name) : ''), [titles])
}
