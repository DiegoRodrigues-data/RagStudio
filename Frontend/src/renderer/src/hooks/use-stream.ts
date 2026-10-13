import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiResult, StreamMessage } from '@/lib/api-types'

export interface StreamState<E = unknown> {
  /** Id of the current (or last) job, or null if none started. */
  id: string | null
  running: boolean
  events: E[]
  lastEvent: E | null
  done: boolean
  /** Exit code of the backend process (null if killed or not finished). */
  code: number | null
  /** Final ApiResult (last JSON line printed by the backend), if any. */
  result: ApiResult | null
  /** Transport-level error (e.g. the IPC call itself failed). */
  error: string | null
}

export interface UseStream<E = unknown> extends StreamState<E> {
  /** Start a job from a raw argv (`['experiments', 'run', '--id', 'x']`). */
  start: (argv: string[]) => Promise<string>
  /** Start a job through an `api.*` streaming helper: `startWith(id => api.experiments.run(id, expId))`. */
  startWith: (starter: (streamId: string) => Promise<void>) => Promise<string>
  cancel: () => Promise<void>
  reset: () => void
}

const initial = <E>(): StreamState<E> => ({
  id: null,
  running: false,
  events: [],
  lastEvent: null,
  done: false,
  code: null,
  result: null,
  error: null
})

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

/**
 * Manage a single streaming backend job. Only one job is tracked at a time;
 * starting a new one resets the state (the previous job keeps running in the
 * backend unless `cancel()` was called first).
 */
export function useStream<E = unknown>(): UseStream<E> {
  const [state, setState] = useState<StreamState<E>>(initial<E>)
  const idRef = useRef<string | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined' || !window.api) return
    const unsubscribe = window.api.onProgress((msg: StreamMessage) => {
      if (!idRef.current || msg.id !== idRef.current) return
      setState((prev) => {
        if (msg.done) {
          return {
            ...prev,
            running: false,
            done: true,
            code: msg.code ?? null,
            result: msg.result ?? null
          }
        }
        const ev = msg.event as E
        return { ...prev, events: [...prev.events, ev], lastEvent: ev }
      })
    })
    return unsubscribe
  }, [])

  const begin = useCallback((): string => {
    const id = newId()
    idRef.current = id
    setState({ ...initial<E>(), id, running: true })
    return id
  }, [])

  const fail = useCallback((id: string, e: unknown) => {
    if (idRef.current !== id) return
    setState((prev) => ({
      ...prev,
      running: false,
      done: true,
      error: (e as Error)?.message ?? String(e)
    }))
  }, [])

  const start = useCallback(
    async (argv: string[]): Promise<string> => {
      const id = begin()
      try {
        await window.api.stream(id, argv)
      } catch (e) {
        fail(id, e)
      }
      return id
    },
    [begin, fail]
  )

  const startWith = useCallback(
    async (starter: (streamId: string) => Promise<void>): Promise<string> => {
      const id = begin()
      try {
        await starter(id)
      } catch (e) {
        fail(id, e)
      }
      return id
    },
    [begin, fail]
  )

  const cancel = useCallback(async () => {
    const id = idRef.current
    if (!id) return
    await window.api.cancelStream(id)
  }, [])

  const reset = useCallback(() => {
    idRef.current = null
    setState(initial<E>())
  }, [])

  return { ...state, start, startWith, cancel, reset }
}
