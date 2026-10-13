import type { ElectronAPI } from '@electron-toolkit/preload'
import type { RagStudioApi } from '../renderer/src/lib/api-types'

declare global {
  interface Window {
    electron: ElectronAPI
    api: RagStudioApi
  }
}

export {}
