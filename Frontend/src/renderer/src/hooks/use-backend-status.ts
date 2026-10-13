import { useContext } from 'react'
import { BackendStatusContext, type BackendStatusValue } from '@/lib/backend-status'

export function useBackendStatus(): BackendStatusValue {
  const ctx = useContext(BackendStatusContext)
  if (!ctx) throw new Error('useBackendStatus must be used inside <BackendStatusProvider>')
  return ctx
}
