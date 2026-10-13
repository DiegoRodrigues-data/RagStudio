import { BrowserWindow, dialog, ipcMain, shell, type IpcMainInvokeEvent } from 'electron'
import { cancelPythonStream, getPaths, runPython, startPythonStream } from './python'
import type { FileFilter, StreamMessage } from '../renderer/src/lib/api-types'

export const CHANNELS = {
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

function assertStringArray(value: unknown, name: string): string[] {
  if (!Array.isArray(value) || !value.every((v) => typeof v === 'string')) {
    throw new TypeError(`${name} must be an array of strings`)
  }
  return value
}

function windowOf(event: IpcMainInvokeEvent): BrowserWindow | undefined {
  return BrowserWindow.fromWebContents(event.sender) ?? undefined
}

export function registerIpc(): void {
  ipcMain.handle(CHANNELS.run, (_e, argv: unknown) => runPython(assertStringArray(argv, 'argv')))

  ipcMain.handle(CHANNELS.stream, (event, id: unknown, argv: unknown) => {
    if (typeof id !== 'string' || !id) throw new TypeError('id must be a non-empty string')
    const sender = event.sender
    const send = (msg: StreamMessage): void => {
      if (!sender.isDestroyed()) sender.send(CHANNELS.progress, msg)
    }
    startPythonStream(id, assertStringArray(argv, 'argv'), send)
  })

  ipcMain.handle(CHANNELS.cancel, (_e, id: unknown) => {
    if (typeof id === 'string') cancelPythonStream(id)
  })

  ipcMain.handle(CHANNELS.openDirectory, async (event) => {
    const win = windowOf(event)
    const opts = { properties: ['openDirectory', 'createDirectory'] as const }
    const r = win
      ? await dialog.showOpenDialog(win, { properties: [...opts.properties] })
      : await dialog.showOpenDialog({ properties: [...opts.properties] })
    return r.canceled || r.filePaths.length === 0 ? null : r.filePaths[0]
  })

  ipcMain.handle(CHANNELS.openFiles, async (event, filters?: FileFilter[]) => {
    const win = windowOf(event)
    const options: Electron.OpenDialogOptions = {
      properties: ['openFile', 'multiSelections'],
      filters: Array.isArray(filters) ? filters : undefined
    }
    const r = win ? await dialog.showOpenDialog(win, options) : await dialog.showOpenDialog(options)
    return r.canceled ? [] : r.filePaths
  })

  ipcMain.handle(CHANNELS.saveFile, async (event, defaultPath?: string, filters?: FileFilter[]) => {
    const win = windowOf(event)
    const options: Electron.SaveDialogOptions = {
      defaultPath: typeof defaultPath === 'string' ? defaultPath : undefined,
      filters: Array.isArray(filters) ? filters : undefined
    }
    const r = win ? await dialog.showSaveDialog(win, options) : await dialog.showSaveDialog(options)
    return r.canceled || !r.filePath ? null : r.filePath
  })

  ipcMain.handle(CHANNELS.openPath, async (_e, p: unknown) => {
    if (typeof p !== 'string' || !p) return
    const err = await shell.openPath(p)
    if (err) throw new Error(err)
  })

  ipcMain.handle(CHANNELS.showInFolder, (_e, p: unknown) => {
    if (typeof p === 'string' && p) shell.showItemInFolder(p)
  })

  ipcMain.handle(CHANNELS.getPaths, () => getPaths())
}
