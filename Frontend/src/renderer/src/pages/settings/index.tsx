import { useCallback, useState } from 'react'
import { DatabaseBackup, List, LoaderCircle, PlugZap, Save, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ErrorAlert } from '@/components/shared/error-alert'
import { FieldRow } from '@/components/shared/field-row'
import { LoadingState } from '@/components/shared/loading-state'
import { MockBadge } from '@/components/shared/mock-notice'
import { PageHeader } from '@/components/shared/page-header'
import { Stat } from '@/components/shared/stat'
import { useApiData } from '@/components/shared/use-api-data'
import { usePageT } from '@/components/shared/use-page-t'
import { useBackendStatus } from '@/hooks/use-backend-status'
import { useLanguage } from '@/hooks/use-t'
import { useTheme } from '@/hooks/use-theme'
import { LANGUAGES, type Language, type TranslationKey } from '@/lib/i18n'
import type { Theme } from '@/lib/theme'
import type { ConfigData, DbStatus } from '@/lib/types'
import { dict } from './i18n'

type Edits = Record<string, Record<string, string>>
type TestResult = Awaited<ReturnType<typeof api.config.testConnection>>

const TRUE = new Set(['1', 'true', 'yes', 'on', 'sim'])

export default function SettingsPage(): React.JSX.Element {
  const t = usePageT(dict)
  const { language, setLanguage, t: gt } = useLanguage()
  const { theme, setTheme } = useTheme()
  const backend = useBackendStatus()
  const cfg = useApiData<ConfigData>(useCallback(() => api.config.show(), []))
  const db = useApiData<DbStatus>(useCallback(() => api.db.status(), []))
  const [edits, setEdits] = useState<Edits>({})
  const [busy, setBusy] = useState<string | null>(null)
  const [test, setTest] = useState<TestResult | null>(null)
  const [models, setModels] = useState<string[] | null>(null)

  const value = (section: string, key: string): string =>
    edits[section]?.[key] ?? cfg.data?.[section]?.[key] ?? ''
  const change = (section: string, key: string, v: string): void =>
    setEdits((prev) => ({ ...prev, [section]: { ...(prev[section] ?? {}), [key]: v } }))
  const pending = Object.values(edits).reduce((n, s) => n + Object.keys(s).length, 0)

  const save = async (quiet = false): Promise<boolean> => {
    if (pending === 0) {
      if (!quiet) toast.info(t('nothing'))
      return true
    }
    setBusy('save')
    const res = await api.config.setMany(edits)
    setBusy(null)
    if (!res.ok) {
      toast.error(res.error)
      return false
    }
    cfg.setData(res.data.config)
    setEdits({})
    if (!quiet) toast.success(t('saved', { n: res.data.changed }))
    return true
  }

  const runTest = async (): Promise<void> => {
    if (!(await save(true))) return
    setBusy('test')
    const res = await api.config.testConnection()
    setBusy(null)
    setTest(res)
    cfg.reload()
  }

  const listModels = async (): Promise<void> => {
    if (!(await save(true))) return
    setBusy('models')
    const res = await api.config.listModels()
    setBusy(null)
    if (!res.ok) return void toast.error(res.error)
    setModels(res.data.models)
  }

  const text = (
    section: string,
    key: string,
    label: string,
    opts: { help?: string; mono?: boolean; type?: string; placeholder?: string } = {}
  ): React.JSX.Element => (
    <FieldRow label={label} help={opts.help}>
      <Input
        type={opts.type}
        value={value(section, key)}
        placeholder={opts.placeholder}
        onChange={(e) => change(section, key, e.target.value)}
        className={opts.mono === false ? undefined : 'font-mono text-xs'}
        autoComplete="off"
      />
    </FieldRow>
  )

  const select = (
    section: string,
    key: string,
    label: string,
    options: string[]
  ): React.JSX.Element => (
    <FieldRow label={label}>
      <Select value={value(section, key)} onValueChange={(v) => change(section, key, v)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldRow>
  )

  const toggle = (
    section: string,
    key: string,
    label: string,
    hint?: string
  ): React.JSX.Element => (
    <label className="flex items-start gap-2 text-xs">
      <Switch
        checked={TRUE.has(value(section, key).toLowerCase())}
        onCheckedChange={(v) => change(section, key, v ? 'true' : 'false')}
      />
      <span>
        <span className="font-medium">{label}</span>
        {hint && <span className="block text-muted-foreground">{hint}</span>}
      </span>
    </label>
  )

  const resolved = cfg.data?.provider?.resolved

  return (
    <div className="flex flex-col gap-4">
      <PageHeader>
        {pending > 0 && <Badge variant="outline">{t('unsaved', { n: pending })}</Badge>}
        <Button size="sm" onClick={() => void save()} disabled={busy !== null || pending === 0}>
          {busy === 'save' ? <LoaderCircle className="animate-spin" /> : <Save />}
          {t('save')}
        </Button>
      </PageHeader>
      <ErrorAlert
        title={t('errorTitle')}
        message={cfg.error}
        retryLabel={gt('common.retry')}
        onRetry={cfg.reload}
      />
      {cfg.loading && !cfg.data ? (
        <LoadingState rows={8} />
      ) : (
        <Tabs defaultValue="provider" className="gap-4">
          <TabsList>
            <TabsTrigger value="provider">{t('tabs.provider')}</TabsTrigger>
            <TabsTrigger value="defaults">{t('tabs.defaults')}</TabsTrigger>
            <TabsTrigger value="appearance">{t('tabs.appearance')}</TabsTrigger>
            <TabsTrigger value="database">{t('tabs.database')}</TabsTrigger>
          </TabsList>

          <TabsContent value="provider" className="grid items-start gap-4 xl:grid-cols-3">
            <section className="flex flex-col gap-3 rounded-lg border bg-card p-4">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold">{t('provider.resolved')}</h3>
                <Badge variant="secondary" className="font-mono">
                  {resolved ?? '–'}
                </Badge>
                <MockBadge provider={resolved} />
              </div>
              <p className="text-xs text-muted-foreground">{t('provider.rule')}</p>
              {select('provider', 'default', t('provider.default'), [
                'auto',
                'openai',
                'lmstudio',
                'ollama',
                'mock'
              ])}
              {text('lm_studio', 'base_url', t('provider.lmstudio'), {
                placeholder: 'http://localhost:1234'
              })}
              {text('ollama', 'base_url', t('provider.ollama'), {
                placeholder: 'http://localhost:11434'
              })}
              <FieldRow label={t('provider.openaiKey')} help={t('provider.openaiKeyHint')}>
                <Input
                  type="password"
                  value={edits.openai?.api_key ?? ''}
                  placeholder={cfg.data?.openai?.api_key || 'sk-...'}
                  onChange={(e) => change('openai', 'api_key', e.target.value)}
                  className="font-mono text-xs"
                  autoComplete="off"
                />
              </FieldRow>
              {text('openai', 'base_url', t('provider.openaiBase'))}
              {text('openai', 'models_allowlist', t('provider.allowlist'), {
                help: t('provider.allowlistHint')
              })}
            </section>

            <section className="flex flex-col gap-3 rounded-lg border bg-card p-4">
              {text('llm', 'model', t('models.llm'))}
              <div className="grid grid-cols-2 gap-2">
                {text('llm', 'temperature', t('models.temperature'))}
                {text('llm', 'max_tokens', t('models.maxTokens'))}
              </div>
              {text('embedding', 'model', t('models.embedding'))}
              <div className="grid grid-cols-2 gap-2">
                {text('embedding', 'batch_size', t('models.batch'))}
                {text('provider', 'max_retries', t('models.retries'))}
                {text('provider', 'timeout_llm', t('models.timeoutLlm'))}
                {text('provider', 'timeout_embedding', t('models.timeoutEmbedding'))}
              </div>
            </section>

            <section className="flex flex-col gap-3 rounded-lg border bg-card p-4">
              <p className="text-xs text-muted-foreground">{t('provider.testHint')}</p>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void runTest()} disabled={busy !== null}>
                  {busy === 'test' ? <LoaderCircle className="animate-spin" /> : <PlugZap />}
                  {t('provider.test')}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => void listModels()}
                  disabled={busy !== null}
                >
                  {busy === 'models' ? <LoaderCircle className="animate-spin" /> : <List />}
                  {t('provider.models')}
                </Button>
              </div>
              {test && !test.ok && (
                <Alert variant="destructive">
                  <AlertTitle>{t('provider.testFail')}</AlertTitle>
                  <AlertDescription>{test.error}</AlertDescription>
                </Alert>
              )}
              {test && test.ok && (
                <Alert variant={test.data.ok ? 'default' : 'destructive'}>
                  <AlertTitle>
                    {test.data.ok ? t('provider.testOk') : t('provider.testFail')} ·{' '}
                    <span className="font-mono">{test.data.provider}</span>
                  </AlertTitle>
                  <AlertDescription>
                    <ul className="flex flex-col gap-1 font-mono text-xs">
                      {(['embedding', 'llm'] as const).map((kind) => {
                        const part = test.data[kind]
                        return (
                          <li key={kind} className="break-words">
                            {kind}: {part.ok ? `ok · ${part.model}` : part.error}
                          </li>
                        )
                      })}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
              {models && (
                <div>
                  <div className="mb-1 text-xs font-medium">{t('models.available')}</div>
                  <ul className="flex max-h-72 flex-col gap-0.5 overflow-auto rounded-md border bg-muted/40 p-2 font-mono text-xs">
                    {models.map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          </TabsContent>

          <TabsContent value="defaults">
            <section className="flex max-w-4xl flex-col gap-4 rounded-lg border bg-card p-4">
              <h3 className="text-sm font-semibold">{t('defaults.title')}</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {text('experiments', 'seed', t('defaults.seed'))}
                {text('experiments', 'k', t('defaults.k'))}
                {text('experiments', 'max_context_chars', t('defaults.maxContext'))}
                {select('experiments', 'language', t('defaults.language'), ['pt', 'en'])}
                {select('experiments', 'store', t('defaults.store'), [
                  'memory',
                  'duckdb',
                  'faiss',
                  'chroma'
                ])}
                {select('experiments', 'retrieval_mode', t('defaults.mode'), [
                  'dense',
                  'bm25',
                  'hybrid',
                  'rrf',
                  'mmr'
                ])}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {toggle(
                  'experiments',
                  'fingerprint_probe',
                  t('defaults.fingerprint'),
                  t('defaults.fingerprintHint')
                )}
                {toggle('evaluation', 'judge', t('defaults.judge'))}
              </div>
              <div className="max-w-sm">
                {text('evaluation', 'judge_model', t('defaults.judgeModel'))}
              </div>
            </section>
          </TabsContent>

          <TabsContent value="appearance">
            <section className="flex max-w-2xl flex-col gap-3 rounded-lg border bg-card p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <FieldRow label={t('appearance.theme')}>
                  <Select value={theme} onValueChange={(v) => setTheme(v as Theme)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(['light', 'dark', 'system'] as const).map((o) => (
                        <SelectItem key={o} value={o}>
                          {gt(`theme.${o}`)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FieldRow>
                <FieldRow label={t('appearance.language')}>
                  <Select value={language} onValueChange={(v) => setLanguage(v as Language)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LANGUAGES.map((l) => (
                        <SelectItem key={l} value={l}>
                          {gt(`language.${l}` as TranslationKey)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FieldRow>
              </div>
              <p className="text-xs text-muted-foreground">{t('appearance.hint')}</p>
            </section>
          </TabsContent>

          <TabsContent value="database" className="flex flex-col gap-4">
            <div className="grid gap-2 md:grid-cols-2">
              <Stat label={t('db.path')} value={db.data?.database ?? '–'} mono />
              <Stat label={t('db.version')} value={db.data ? `v${db.data.version}` : '–'} mono />
              <Stat label={t('db.python')} value={backend.paths?.python ?? '–'} mono />
              <Stat label={t('db.root')} value={backend.paths?.projectRoot ?? '–'} mono />
            </div>
            {db.data && (
              <div>
                <div className="mb-1.5 text-xs font-medium">{t('db.counts')}</div>
                <div className="grid grid-cols-3 gap-2 lg:grid-cols-5 xl:grid-cols-9">
                  {Object.entries(db.data.counts).map(([k, v]) => (
                    <Stat key={k} label={k} value={v.toLocaleString()} mono />
                  ))}
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                disabled={busy !== null}
                onClick={async () => {
                  setBusy('backup')
                  const res = await api.db.backup()
                  setBusy(null)
                  if (!res.ok) return void toast.error(res.error)
                  toast.success(t('db.backupDone', { path: res.data.path }))
                }}
              >
                {busy === 'backup' ? <LoaderCircle className="animate-spin" /> : <DatabaseBackup />}
                {t('db.backup')}
              </Button>
              <Button
                variant="outline"
                disabled={busy !== null}
                onClick={async () => {
                  setBusy('integrity')
                  const res = await api.db.integrityCheck()
                  setBusy(null)
                  if (!res.ok) return void toast.error(res.error)
                  if (res.data.ok) toast.success(t('db.integrityOk'))
                  else toast.error(t('db.integrityFail'))
                }}
              >
                {busy === 'integrity' ? <LoaderCircle className="animate-spin" /> : <ShieldCheck />}
                {t('db.integrity')}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  void backend.refresh()
                  db.reload()
                }}
              >
                {t('db.recheck')}
              </Button>
            </div>
            <ErrorAlert title={t('errorTitle')} message={backend.error ?? db.error} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
