import { app, shell, BrowserWindow, net, protocol } from 'electron'
import { join, resolve } from 'path'
import { pathToFileURL } from 'url'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'
import { registerIpc } from './ipc'
import { cancelAllStreams, getPaths } from './python'

// `ragstudio://local/<encoded absolute path>` serves local files (figures, reports) to the renderer
// without opening file:// access. Only paths inside the project root, the data dir or the OS
// temp dir are served.
protocol.registerSchemesAsPrivileged([
  {
    scheme: 'ragstudio',
    privileges: { standard: true, secure: true, supportFetchAPI: true, bypassCSP: false }
  }
])

let cachedRoots: string[] | null = null
function allowedRoots(): string[] {
  return (cachedRoots ??= computeAllowedRoots())
}

function computeAllowedRoots(): string[] {
  const { projectRoot } = getPaths()
  const roots = [projectRoot, app.getPath('temp'), app.getPath('userData')]
  for (const key of ['RAGSTUDIO_DATA_DIR']) {
    const v = process.env[key]
    if (v) roots.push(v)
  }
  return roots.map((r) => resolve(r))
}

function registerLocalProtocol(): void {
  protocol.handle('ragstudio', (request) => {
    const url = new URL(request.url)
    if (url.hostname !== 'local') return new Response('not found', { status: 404 })
    const filePath = resolve(decodeURIComponent(url.pathname))
    const ok = allowedRoots().some((root) => filePath === root || filePath.startsWith(root + '/'))
    if (!ok) return new Response('forbidden', { status: 403 })
    return net.fetch(pathToFileURL(filePath).toString())
  })
}

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    title: 'RagStudio',
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  // In development, mirror renderer console output in the terminal so the
  // app can be verified from logs alone.
  if (is.dev) {
    mainWindow.webContents.on('console-message', (event) => {
      const { level, message, lineNumber, sourceId } = event
      const src = sourceId ? ` (${sourceId.split('/').pop()}:${lineNumber})` : ''
      console.log(`[renderer:${level}] ${message}${src}`)
    })
    mainWindow.webContents.on('did-finish-load', () => console.log('[ragstudio] renderer loaded'))
    mainWindow.webContents.on('render-process-gone', (_e, details) =>
      console.error('[ragstudio] renderer gone:', details.reason)
    )
  }

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('br.usp.ragstudio')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  registerIpc()
  registerLocalProtocol()

  const paths = getPaths()
  console.log(`[ragstudio] projectRoot = ${paths.projectRoot}`)
  console.log(`[ragstudio] python      = ${paths.python}`)
  console.log(`[ragstudio] backend     = ${paths.backendEntry}`)

  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', () => {
  cancelAllStreams()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
