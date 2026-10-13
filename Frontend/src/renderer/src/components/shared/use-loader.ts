import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiResult } from '@/lib/api-types'

export interface Loaded<T> {
  data: T | null
  loading: boolean
  error: string | null
  /** Re-run the loader (also called automatically when `loader` changes). */
  reload: () => Promise<void>
  /** Replace the cached data locally (optimistic updates). */
  setData: (updater: T | null | ((prev: T | null) => T | null)) => void
}

interface State<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Load one backend call and keep its result. Wrap `loader` in `useCallback`; pass `null`
 * to skip loading (e.g. nothing selected yet). Stale responses are ignored.
 */
export function useLoader<T>(loader: (() => Promise<ApiResult<T>>) | null): Loaded<T> {
  const [state, setState] = useState<State<T>>({
    data: null,
    loading: loader !== null,
    error: null
  })
  const seq = useRef(0)

  const reload = useCallback((): Promise<void> => {
    const my = ++seq.current
    if (!loader) {
      return Promise.resolve().then(() => {
        if (my === seq.current) setState({ data: null, loading: false, error: null })
      })
    }
    return Promise.resolve()
      .then(() => {
        if (my === seq.current) setState((s) => ({ ...s, loading: true }))
      })
      .then(() => loader())
      .then((res) => {
        if (my !== seq.current) return
        if (res.ok) setState({ data: res.data, loading: false, error: null })
        else setState((s) => ({ ...s, loading: false, error: res.error }))
      })
  }, [loader])

  useEffect(() => {
    void reload()
  }, [reload])

  const setData = useCallback((updater: T | null | ((prev: T | null) => T | null)): void => {
    setState((s) => ({
      ...s,
      data: typeof updater === 'function' ? (updater as (p: T | null) => T | null)(s.data) : updater
    }))
  }, [])

  return { data: state.data, loading: state.loading, error: state.error, reload, setData }
}
