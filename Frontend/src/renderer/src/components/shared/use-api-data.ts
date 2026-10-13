import { useCallback, useEffect, useState } from 'react'
import type { ApiResult } from '@/lib/api-types'

export interface ApiData<T> {
  data: T | null
  loading: boolean
  error: string | null
  /** Re-run the loader. */
  reload: () => void
  /** Replace the cached data locally (optimistic updates). */
  setData: (updater: T | null | ((prev: T | null) => T | null)) => void
}

/**
 * Load one backend call and keep its result. `loader` is re-invoked whenever its identity
 * changes (wrap it in `useCallback`) or `refreshKey` changes; pass `null` to skip loading
 * (e.g. no selection yet).
 */
export function useApiData<T>(
  loader: (() => Promise<ApiResult<T>>) | null,
  refreshKey: string | number = ''
): ApiData<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let active = true
    const run = async (): Promise<void> => {
      // yield once so state updates never happen synchronously inside the effect body
      await Promise.resolve()
      if (!active) return
      if (!loader) {
        setData(null)
        setError(null)
        setLoading(false)
        return
      }
      setLoading(true)
      const res = await loader()
      if (!active) return
      if (res.ok) {
        setData(res.data)
        setError(null)
      } else {
        setError(res.error)
      }
      setLoading(false)
    }
    void run()
    return () => {
      active = false
    }
  }, [loader, version, refreshKey])

  const reload = useCallback(() => setVersion((v) => v + 1), [])

  const set = useCallback((updater: T | null | ((prev: T | null) => T | null)) => {
    setData((prev) =>
      typeof updater === 'function' ? (updater as (p: T | null) => T | null)(prev) : updater
    )
  }, [])

  return { data, loading, error, reload, setData: set }
}
