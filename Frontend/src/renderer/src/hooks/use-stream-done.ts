import { useEffect, useRef } from 'react'
import type { ApiResult } from '@/lib/api-types'

interface StreamLike {
  running: boolean
  result: ApiResult | null
  error: string | null
  code: number | null
}

/**
 * Call `handler` once each time a streaming job finishes (running: true -> false).
 * The handler always sees the latest props/state of the component.
 */
export function useStreamDone(stream: StreamLike, handler: (stream: StreamLike) => void): void {
  const handlerRef = useRef(handler)
  const wasRunning = useRef(false)
  useEffect(() => {
    handlerRef.current = handler
  })
  useEffect(() => {
    if (wasRunning.current && !stream.running) handlerRef.current(stream)
    wasRunning.current = stream.running
  }, [stream])
}
