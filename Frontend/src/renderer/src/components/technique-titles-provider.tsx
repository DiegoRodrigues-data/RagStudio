import { useCallback, useMemo, type ReactNode } from 'react'
import { api } from '@/lib/api'
import { TechniqueTitlesContext } from '@/lib/technique-titles'
import { useApiData } from '@/components/shared/use-api-data'
import type { TechniqueInfo } from '@/lib/types'

/** Loads the technique catalog once so every screen can show display names instead of identifiers. */
export function TechniqueTitlesProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const list = useApiData<TechniqueInfo[]>(useCallback(() => api.techniques.list(), []))
  const titles = useMemo(
    () => Object.fromEntries((list.data ?? []).map((x) => [x.name, x.title || x.name])),
    [list.data]
  )
  return (
    <TechniqueTitlesContext.Provider value={titles}>{children}</TechniqueTitlesContext.Provider>
  )
}
