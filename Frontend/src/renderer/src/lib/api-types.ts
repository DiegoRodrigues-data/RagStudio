/**
 * Shared types for the Electron IPC bridge (`window.api`) and the Python
 * backend contract. This file is imported (types only) by the main process,
 * the preload script and the renderer.
 */

/** Successful backend response. */
export interface ApiOk<T = unknown> {
  ok: true
  data: T
  warnings?: string[]
}

/** Failed backend response (also used for transport-level failures). */
export interface ApiErr {
  ok: false
  error: string
  warnings?: string[]
  /** Process exit code, when the failure came from the Python process. */
  code?: number | null
}

export type ApiResult<T = unknown> = ApiOk<T> | ApiErr

/** Message delivered on the `python:progress` channel for streaming jobs. */
export interface StreamMessage<T = unknown> {
  id: string
  /** A JSON line emitted by the backend while running. */
  event?: T
  /** Present (true) on the final message of a stream. */
  done?: boolean
  /** Process exit code (null if killed by signal). */
  code?: number | null
  /** The last JSON line printed by the backend, if any. */
  result?: ApiResult
}

export interface FileFilter {
  name: string
  extensions: string[]
}

export interface AppPaths {
  projectRoot: string
  python: string
  backendEntry: string
}

/** The API exposed by the preload script as `window.api`. */
export interface RagStudioApi {
  run(argv: string[]): Promise<ApiResult>
  stream(id: string, argv: string[]): Promise<void>
  cancelStream(id: string): Promise<void>
  onProgress(cb: (msg: StreamMessage) => void): () => void
  openDirectory(): Promise<string | null>
  openFiles(filters?: FileFilter[]): Promise<string[]>
  saveFile(defaultPath?: string, filters?: FileFilter[]): Promise<string | null>
  openPath(path: string): Promise<void>
  showInFolder(path: string): Promise<void>
  getPaths(): Promise<AppPaths>
}
