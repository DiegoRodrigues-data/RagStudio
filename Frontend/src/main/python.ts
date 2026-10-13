import { app } from 'electron'
import { spawn, type ChildProcess } from 'child_process'
import { existsSync } from 'fs'
import { homedir } from 'os'
import path from 'path'
import type { ApiResult, StreamMessage } from '../renderer/src/lib/api-types'

const ENV_NAME = 'ragstudio'

const CONDA_BASES = [
  '~/miniconda3',
  '~/miniforge3',
  '~/anaconda3',
  '~/mambaforge',
  '/opt/miniconda3',
  '/opt/miniforge3',
  '/opt/anaconda3',
  '/opt/homebrew/Caskroom/miniforge/base',
  '/opt/homebrew/Caskroom/miniconda/base'
]

function expandHome(p: string): string {
  return p.startsWith('~') ? path.join(homedir(), p.slice(1)) : p
}

/**
 * Resolve the Python interpreter:
 *  1. `RAGSTUDIO_PYTHON` env var
 *  2. `<base>/envs/ragstudio/bin/python` (or `python.exe` on Windows) for known conda bases
 *  3. plain `python` from PATH
 */
export function resolvePython(): string {
  const fromEnv = process.env.RAGSTUDIO_PYTHON
  if (fromEnv && fromEnv.trim()) return fromEnv.trim()

  const bin = process.platform === 'win32' ? ['python.exe'] : ['bin', 'python']
  for (const base of CONDA_BASES) {
    const candidate = path.join(expandHome(base), 'envs', ENV_NAME, ...bin)
    if (existsSync(candidate)) return candidate
  }
  return 'python'
}

/**
 * Project root = parent of `Frontend/`.
 * In dev `app.getAppPath()` is the Frontend folder. When packaged we try a few
 * locations relative to `process.resourcesPath` and pick the first one that
 * contains the `ragstudio/cli.py` package entry.
 */
export function resolveProjectRoot(): string {
  const fromEnv = process.env.RAGSTUDIO_PROJECT_ROOT
  if (fromEnv && fromEnv.trim()) return path.resolve(fromEnv.trim())

  const appPath = app.getAppPath()
  const candidates: string[] = []

  if (!app.isPackaged) {
    candidates.push(path.resolve(appPath, '..'))
  } else {
    const res = process.resourcesPath
    candidates.push(
      path.resolve(res, 'project'), // extraResources: the ragstudio package copied next to the app
      path.resolve(res, '..'), // <App>/Contents
      path.resolve(res, '..', '..'), // <App>.app
      path.resolve(res, '..', '..', '..'), // folder containing the .app bundle
      path.resolve(appPath, '..')
    )
  }

  for (const c of candidates) {
    if (existsSync(path.join(c, 'ragstudio', 'cli.py'))) return c
  }
  return candidates[0]
}

export function backendEntry(projectRoot = resolveProjectRoot()): string {
  return path.join(projectRoot, 'ragstudio', 'cli.py')
}

type Paths = { projectRoot: string; python: string; backendEntry: string }
let cachedPaths: Paths | null = null

/** Resolved once: interpreter and project root cannot change while the app is running. */
export function getPaths(): Paths {
  if (!cachedPaths) {
    const projectRoot = resolveProjectRoot()
    cachedPaths = { projectRoot, python: resolvePython(), backendEntry: backendEntry(projectRoot) }
  }
  return cachedPaths
}

function spawnBackend(argv: string[]): ChildProcess {
  // The backend is a package: `python -m ragstudio <group> <command> ...` with cwd = project root.
  const { projectRoot, python } = getPaths()
  return spawn(python, ['-m', 'ragstudio', ...argv], {
    cwd: projectRoot,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true
  })
}

function tail(text: string, maxLines = 20): string {
  const lines = text.trim().split(/\r?\n/)
  return lines.slice(-maxLines).join('\n')
}

function isApiResult(value: unknown): value is ApiResult {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as { ok?: unknown }).ok === 'boolean'
  )
}

function tryParseJson(line: string): unknown | undefined {
  const trimmed = line.trim()
  if (!trimmed || (trimmed[0] !== '{' && trimmed[0] !== '[')) return undefined
  try {
    return JSON.parse(trimmed)
  } catch {
    return undefined
  }
}

function lastJsonLine(stdout: string): unknown | undefined {
  const lines = stdout.split(/\r?\n/)
  for (let i = lines.length - 1; i >= 0; i--) {
    if (!lines[i].trim()) continue
    return tryParseJson(lines[i])
  }
  return undefined
}

function toApiResult(parsed: unknown, code: number | null, stderr: string): ApiResult {
  if (isApiResult(parsed)) return parsed
  if (parsed !== undefined) {
    return {
      ok: false,
      error: `Backend returned JSON with an unexpected shape: ${JSON.stringify(parsed).slice(0, 500)}`,
      code
    }
  }
  const err = tail(stderr)
  return {
    ok: false,
    error: err || `Backend exited with code ${code ?? 'null'} and produced no JSON output`,
    code
  }
}

/**
 * Run `python -m ragstudio ...argv` and resolve the last JSON line of
 * stdout as an ApiResult. Never rejects.
 */
export function runPython(argv: string[]): Promise<ApiResult> {
  return new Promise((resolve) => {
    let settled = false
    const finish = (r: ApiResult): void => {
      if (settled) return
      settled = true
      resolve(r)
    }

    let child: ChildProcess
    try {
      child = spawnBackend(argv)
    } catch (e) {
      finish({ ok: false, error: `Failed to spawn Python: ${(e as Error).message}` })
      return
    }

    let stdout = ''
    let stderr = ''
    child.stdout?.setEncoding('utf8')
    child.stderr?.setEncoding('utf8')
    child.stdout?.on('data', (d: string) => (stdout += d))
    child.stderr?.on('data', (d: string) => (stderr += d))

    child.on('error', (err) => {
      finish({
        ok: false,
        error: `Failed to start Python (${resolvePython()}): ${err.message}`
      })
    })

    child.on('close', (code) => {
      const parsed = lastJsonLine(stdout)
      finish(toApiResult(parsed, code, stderr))
    })
  })
}

// ---------------------------------------------------------------------------
// Streaming
// ---------------------------------------------------------------------------

type Sender = (msg: StreamMessage) => void

interface RunningJob {
  child: ChildProcess
  killTimer?: NodeJS.Timeout
}

const running = new Map<string, RunningJob>()

/**
 * Spawn the backend and forward every JSON line of stdout to `send` as
 * `{ id, event }`. On exit sends `{ id, done: true, code, result }`.
 */
export function startPythonStream(id: string, argv: string[], send: Sender): void {
  if (running.has(id)) {
    send({
      id,
      done: true,
      code: null,
      result: { ok: false, error: `A stream with id "${id}" is already running` }
    })
    return
  }

  let child: ChildProcess
  try {
    child = spawnBackend(argv)
  } catch (e) {
    send({
      id,
      done: true,
      code: null,
      result: { ok: false, error: `Failed to spawn Python: ${(e as Error).message}` }
    })
    return
  }

  const job: RunningJob = { child }
  running.set(id, job)

  let buffer = ''
  let stderr = ''
  let lastJson: unknown
  let finished = false

  const handleLine = (line: string): void => {
    const parsed = tryParseJson(line)
    if (parsed === undefined) return
    lastJson = parsed
    // The backend's final contract line ({ok, data|error}) is delivered as `result` on exit,
    // not as a progress event, so `lastEvent` in the renderer stays the last real progress line.
    const isFinal =
      typeof parsed === 'object' &&
      parsed !== null &&
      'ok' in (parsed as Record<string, unknown>) &&
      !('progress' in (parsed as Record<string, unknown>))
    if (!isFinal) send({ id, event: parsed })
  }

  child.stdout?.setEncoding('utf8')
  child.stderr?.setEncoding('utf8')
  child.stdout?.on('data', (chunk: string) => {
    buffer += chunk
    let idx: number
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 1)
      handleLine(line)
    }
  })
  child.stderr?.on('data', (chunk: string) => {
    stderr += chunk
    if (stderr.length > 64_000) stderr = stderr.slice(-32_000)
  })

  const finish = (code: number | null, spawnError?: Error): void => {
    if (finished) return
    finished = true
    if (buffer.trim()) handleLine(buffer)
    if (job.killTimer) clearTimeout(job.killTimer)
    running.delete(id)

    let result: ApiResult | undefined
    if (spawnError) {
      result = { ok: false, error: `Failed to start Python: ${spawnError.message}` }
    } else if (lastJson !== undefined) {
      result = toApiResult(lastJson, code, stderr)
    } else if (code !== 0) {
      result = toApiResult(undefined, code, stderr)
    }
    send({ id, done: true, code, result })
  }

  child.on('error', (err) => finish(null, err))
  child.on('close', (code) => finish(code))
}

/** SIGTERM the job, escalating to SIGKILL after 5 seconds. */
export function cancelPythonStream(id: string): void {
  const job = running.get(id)
  if (!job) return
  const { child } = job
  if (child.exitCode !== null || child.signalCode !== null) return
  try {
    child.kill('SIGTERM')
  } catch {
    /* ignore */
  }
  job.killTimer = setTimeout(() => {
    if (child.exitCode === null && child.signalCode === null) {
      try {
        child.kill('SIGKILL')
      } catch {
        /* ignore */
      }
    }
  }, 5000)
}

/** Kill every running stream (used on app quit). */
export function cancelAllStreams(): void {
  for (const id of Array.from(running.keys())) cancelPythonStream(id)
}
