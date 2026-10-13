import { createContext } from 'react'
import type { ApiResult, AppPaths } from './api-types'

export type BackendState = 'checking' | 'ok' | 'error'

export interface BackendStatusValue {
  state: BackendState
  /** Result of the last `db status` call (null while checking). */
  result: ApiResult | null
  /** Human readable error when `state === 'error'`. */
  error: string | null
  paths: AppPaths | null
  /** Timestamp (ms) of the last check, 0 if never. */
  checkedAt: number
  refresh: () => Promise<void>
}

export const BackendStatusContext = createContext<BackendStatusValue | null>(null)
