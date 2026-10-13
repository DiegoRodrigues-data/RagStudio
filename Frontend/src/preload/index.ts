import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'
import type {
  ApiResult,
  FileFilter,
  RagStudioApi,
  StreamMessage
} from '../renderer/src/lib/api-types'

// Channel names are duplicated here (instead of importing from ../main/ipc)
// so the preload bundle never pulls main-process code.
const CH = {
  run: 'python:run',
  stream: 'python:stream',
  cancel: 'python:cancel',
  progress: 'python:progress',
  openDirectory: 'dialog:openDirectory',
  openFiles: 'dialog:openFiles',
  saveFile: 'dialog:saveFile',
  openPath: 'shell:openPath',
  showInFolder: 'shell:showInFolder',
  getPaths: 'app:getPaths'
} as const

const api: RagStudioApi = {
  run: (argv: string[]): Promise<ApiResult> => ipcRenderer.invoke(CH.run, argv),
  stream: (id: string, argv: string[]): Promise<void> => ipcRenderer.invoke(CH.stream, id, argv),
  cancelStream: (id: string): Promise<void> => ipcRenderer.invoke(CH.cancel, id),
  onProgress: (cb: (msg: StreamMessage) => void): (() => void) => {
    const listener = (_e: IpcRendererEvent, msg: StreamMessage): void => cb(msg)
    ipcRenderer.on(CH.progress, listener)
    return () => {
      ipcRenderer.removeListener(CH.progress, listener)
    }
  },
  openDirectory: (): Promise<string | null> => ipcRenderer.invoke(CH.openDirectory),
  openFiles: (filters?: FileFilter[]): Promise<string[]> =>
    ipcRenderer.invoke(CH.openFiles, filters),
  saveFile: (defaultPath?: string, filters?: FileFilter[]): Promise<string | null> =>
    ipcRenderer.invoke(CH.saveFile, defaultPath, filters),
  openPath: (path: string): Promise<void> => ipcRenderer.invoke(CH.openPath, path),
  showInFolder: (path: string): Promise<void> => ipcRenderer.invoke(CH.showInFolder, path),
  getPaths: () => ipcRenderer.invoke(CH.getPaths)
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
}
