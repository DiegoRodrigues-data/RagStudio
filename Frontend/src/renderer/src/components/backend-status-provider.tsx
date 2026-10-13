import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from '@/lib/api'
import type { ApiResult, AppPaths } from '@/lib/api-types'
import { BackendStatusContext, type BackendState } from '@/lib/backend-status'

interface Snapshot {
  state: BackendState
  result: ApiResult | null
  error: string | null
  paths: AppPaths | null
  checkedAt: number
}

const initial: Snapshot = {
  state: 'checking',
  result: null,
  error: null,
  paths: null,
  checkedAt: 0
}

/**
 * Calls `getPaths()` and `db status` once on startup (and on demand through
 * `refresh()`); a failing backend is expected and reported, never thrown.
 */
export function BackendStatusProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [snap, setSnap] = useState<Snapshot>(initial)
  const inflight = useRef<Promise<void> | null>(null)

  const refresh = useCallback(async (): Promise<void> => {
    if (inflight.current) return inflight.current
    const run = (async (): Promise<void> => {
      setSnap((prev) => ({ ...prev, state: 'checking', error: null }))

      let paths: AppPaths | null = null
      try {
        paths = window.api ? await window.api.getPaths() : null
      } catch (e) {
        paths = null
        console.warn('[backend-status] getPaths failed', e)
      }

      const result = await api.db.status()
      if (result.ok) {
        console.info('[backend-status] backend OK', paths?.python)
      } else {
        console.warn('[backend-status] backend unavailable:', result.error)
      }
      setSnap({
        state: result.ok ? 'ok' : 'error',
        result,
        error: result.ok ? null : result.error,
        paths,
        checkedAt: Date.now()
      })
    })()
    inflight.current = run
    try {
      await run
    } finally {
      inflight.current = null
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo(() => ({ ...snap, refresh }), [snap, refresh])

  return <BackendStatusContext.Provider value={value}>{children}</BackendStatusContext.Provider>
}
