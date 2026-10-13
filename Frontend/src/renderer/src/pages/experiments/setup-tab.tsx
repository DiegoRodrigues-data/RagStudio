import { Fragment, useCallback, useMemo, useState } from 'react'
import { Eye, LoaderCircle, Play, Plus, Save, TriangleAlert, X } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { ToggleChips } from '@/components/shared/chips'
import { FieldRow } from '@/components/shared/field-row'
import { fmtMetric } from '@/components/shared/metrics'
import { MockBadge } from '@/components/shared/mock-notice'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import type {
  ConfigData,
  CorpusDetail,
  CorpusSummary,
  PreviewResult,
  QuestionSetSummary,
  RunbookOption,
  RunbookOptions,
  TechniqueInfo
} from '@/lib/types'
import { cn } from '@/lib/utils'
import { useT } from '@/hooks/use-t'
import { useTechniqueTitle } from '@/hooks/use-technique-title'
import { STAGES, axisKey, stageKey } from '@/lib/stages'
import { TechniqueStatusBadge } from '@/pages/techniques/status-badge'
import {
  MODES,
  RERANKERS,
  STORES,
  STRATEGIES,
  applyPreset,
  buildConfig,
  emptyDraft,
  type Draft
} from './draft'
import type { ExpKey } from './i18n'

function Section({
  n,
  title,
  badge,
  aside,
  children,
  className
}: {
  n: number
  title: string
  badge?: string
  aside?: React.ReactNode
  children: React.ReactNode
  className?: string
}): React.JSX.Element {
  return (
    <section className={cn('flex min-w-0 flex-col rounded-lg border bg-card', className)}>
      <header className="flex items-center gap-2 border-b px-3 py-2">
        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground">
          {n}
        </span>
        <h3 className="truncate text-sm font-semibold">{title}</h3>
        {badge && <Badge variant="secondary">{badge}</Badge>}
        {aside && <div className="ml-auto flex items-center gap-1">{aside}</div>}
      </header>
      <div className="flex flex-col gap-3 p-3">{children}</div>
    </section>
  )
}

function Group({
  title,
  children
}: {
  title: string
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
        {title}
      </div>
      {children}
    </div>
  )
}

/** Index requirements a technique declares, with the label that explains them. */
const INDEX_NEEDS: Record<string, ExpKey> = {
  'index:parent_child': 'setup.tech.needs.parent_child',
  'index:contextual': 'setup.tech.needs.contextual'
}

export function SetupTab({
  t,
  onCreated
}: {
  t: PageT<ExpKey>
  onCreated: (id: string, run: boolean) => void
}): React.JSX.Element {
  const corpora = useApiData<CorpusSummary[]>(useCallback(() => api.corpus.list(), []))
  const sets = useApiData<QuestionSetSummary[]>(useCallback(() => api.questions.sets(), []))
  const catalog = useApiData<TechniqueInfo[]>(useCallback(() => api.techniques.list(), []))
  const gt = useT()
  const techTitle = useTechniqueTitle()
  const cfg = useApiData<ConfigData>(useCallback(() => api.config.show(), []))
  const presets = useApiData<Record<string, Record<string, unknown>>>(
    useCallback(() => api.experiments.presets(), [])
  )
  const options = useApiData<RunbookOptions>(useCallback(() => api.experiments.options(), []))
  const missing = useMemo(() => {
    const pick = (rows: RunbookOption[] | undefined): Record<string, string> =>
      Object.fromEntries((rows ?? []).filter((o) => o.requires).map((o) => [o.name, o.requires!]))
    return { rerankers: pick(options.data?.rerankers), stores: pick(options.data?.stores) }
  }, [options.data])

  const [edited, setEdited] = useState<Draft | null>(null)
  const defaults = useMemo(
    () =>
      emptyDraft({
        k: cfg.data?.experiments?.k,
        seed: cfg.data?.experiments?.seed,
        language: cfg.data?.experiments?.language,
        maxContext: cfg.data?.experiments?.max_context_chars,
        mode: cfg.data?.experiments?.retrieval_mode
      }),
    [cfg.data]
  )
  const draft = edited ?? defaults
  const set = <K extends keyof Draft>(key: K, value: Draft[K]): void =>
    setEdited({ ...draft, [key]: value })

  const techniques = useMemo(() => catalog.data ?? [], [catalog.data])
  /** Catalog in pipeline order, so the list reads as the flow of an experiment. */
  const byStage = useMemo(
    () =>
      [...techniques].sort(
        (a, b) =>
          (STAGES as readonly string[]).indexOf(a.stage) -
            (STAGES as readonly string[]).indexOf(b.stage) ||
          (a.title || a.name).localeCompare(b.title || b.name)
      ),
    [techniques]
  )
  const corpusName = draft.corpus || corpora.data?.[0]?.name || ''
  const questionSet = draft.questionSet || sets.data?.[0]?.name || ''
  const corpusLoader = useMemo(
    () => (corpusName ? () => api.corpus.describe(corpusName) : null),
    [corpusName]
  )
  const corpus = useApiData<CorpusDetail>(corpusLoader)
  const splitNames = Object.keys(corpus.data?.split_documents ?? {})
  const questionCount = sets.data?.find((s) => s.name === questionSet)?.questions

  const built = useMemo(
    () => buildConfig(draft, techniques, { corpus: corpusName, questionSet }),
    [draft, techniques, corpusName, questionSet]
  )
  const signature = built.ok ? JSON.stringify(built.config) : ''

  const [preview, setPreview] = useState<{ signature: string; data: PreviewResult } | null>(null)
  const [busy, setBusy] = useState<'preview' | 'create' | 'run' | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)
  const fresh = preview !== null && preview.signature === signature

  const localError = built.ok
    ? null
    : built.error.key === 'err.param'
      ? t('err.param', built.error.vars)
      : t(built.error.key)

  const runPreview = async (): Promise<void> => {
    if (!built.ok) return
    setBusy('preview')
    setServerError(null)
    const res = await api.experiments.preview(built.config)
    setBusy(null)
    if (!res.ok) return setServerError(res.error)
    setPreview({ signature, data: res.data })
  }

  const create = async (run: boolean): Promise<void> => {
    if (!built.ok) return
    setBusy(run ? 'run' : 'create')
    setServerError(null)
    const res = await api.experiments.create(built.config)
    setBusy(null)
    if (!res.ok) return setServerError(res.error)
    toast.success(t('review.created', { n: res.data.runs }))
    onCreated(res.data.id, run)
  }

  const toggleTechnique = (name: string, on: boolean): void =>
    set(
      'techniques',
      techniques.map((x) => x.name).filter((n) => (n === name ? on : draft.techniques.includes(n)))
    )

  const setParam = (technique: string, param: string, value: string): void =>
    set('params', {
      ...draft.params,
      [technique]: { ...(draft.params[technique] ?? {}), [param]: value }
    })

  const setChunk = (i: number, patch: Partial<Draft['chunking'][number]>): void =>
    set(
      'chunking',
      draft.chunking.map((row, j) => (j === i ? { ...row, ...patch } : row))
    )

  const provider = cfg.data?.provider?.resolved
  const defaultLlm = provider === 'mock' ? 'mock-llm' : cfg.data?.llm?.model
  const defaultEmbedding = provider === 'mock' ? 'mock-embed' : cfg.data?.embedding?.model
  const est = fresh ? preview.data.estimate : null
  const pruned = fresh ? preview.data.pruned : null
  const prunedNote = pruned
    ? [
        pruned.redundant + pruned.incompatible > 0
          ? t('review.pruned', {
              n: pruned.redundant + pruned.incompatible,
              redundant: pruned.redundant,
              incompatible: pruned.incompatible
            })
          : '',
        pruned.without_runs.length > 0
          ? t('review.withoutRuns', { names: pruned.without_runs.map(techTitle).join(', ') })
          : ''
      ]
        .filter(Boolean)
        .join(' ')
    : ''
  /** Before the preview the run count is the full grid: an upper bound when something may be pruned. */
  const mayPrune = techniques.some(
    (x) =>
      draft.techniques.includes(x.name) &&
      (x.ignores.some((a) => a !== 'max_context_chars') || x.requires.some((r) => r in INDEX_NEEDS))
  )

  return (
    <div className="flex flex-col gap-3">
      <div className="grid items-start gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.1fr)_minmax(0,1.1fr)]">
        {/* ------------------------------------------------------------------ 1. data */}
        <Section n={1} title={t('setup.step.data')} aside={<MockBadge provider={provider} />}>
          <FieldRow label={t('setup.name')}>
            <Input value={draft.name} onChange={(e) => set('name', e.target.value)} />
          </FieldRow>
          <FieldRow label={t('setup.description')}>
            <Input value={draft.description} onChange={(e) => set('description', e.target.value)} />
          </FieldRow>
          <FieldRow
            label={t('setup.corpus')}
            help={corpora.data?.length === 0 ? t('setup.noCorpus') : undefined}
          >
            <Select
              value={corpusName}
              onValueChange={(v) => setEdited({ ...draft, corpus: v, split: 'none' })}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(corpora.data ?? []).map((c) => (
                  <SelectItem key={c.id} value={c.name}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FieldRow>
          <div className="grid grid-cols-2 gap-2">
            <FieldRow label={t('setup.split')}>
              <Select value={draft.split} onValueChange={(v) => set('split', v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t('setup.noSplit')}</SelectItem>
                  {splitNames.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldRow>
            <FieldRow label={t('setup.limit')}>
              <Input
                value={draft.limit}
                onChange={(e) => set('limit', e.target.value)}
                className="font-mono"
                placeholder={t('setup.limitHint')}
                inputMode="numeric"
              />
            </FieldRow>
          </div>
          <FieldRow
            label={t('setup.questionSet')}
            help={sets.data?.length === 0 ? t('setup.noQuestions') : undefined}
          >
            <Select value={questionSet} onValueChange={(v) => set('questionSet', v)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(sets.data ?? []).map((s) => (
                  <SelectItem key={s.id} value={s.name}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FieldRow>
          {corpus.data && (
            <p className="rounded-md bg-muted/50 px-2 py-1.5 text-xs text-muted-foreground">
              {t('setup.dataSummary', {
                docs:
                  draft.split === 'none'
                    ? corpus.data.documents.length
                    : (corpus.data.split_documents[draft.split]?.length ?? 0),
                questions: questionCount ?? '–'
              })}
            </p>
          )}
          {presets.data && (
            <Group title={t('setup.presets')}>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(presets.data).map(([name, preset]) => (
                  <Button
                    key={name}
                    variant="outline"
                    size="xs"
                    onClick={() => setEdited(applyPreset(draft, preset, techniques))}
                  >
                    {name}
                  </Button>
                ))}
              </div>
            </Group>
          )}
          <Group title={t('setup.group.control')}>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 text-xs" title={t('setup.judgeHint')}>
                <Switch checked={draft.judge} onCheckedChange={(v) => set('judge', v)} />
                <span className="font-medium">{t('setup.judge')}</span>
              </label>
              <FieldRow label={t('setup.budget')}>
                <Input
                  value={draft.budget}
                  onChange={(e) => set('budget', e.target.value)}
                  className="h-7 font-mono text-xs"
                  inputMode="decimal"
                  title={t('setup.budgetHint')}
                />
              </FieldRow>
            </div>
            {draft.judge && (
              <FieldRow label={t('setup.judgeModel')}>
                <Input
                  value={draft.judgeModel}
                  placeholder={defaultLlm}
                  onChange={(e) => set('judgeModel', e.target.value)}
                  className="h-7 font-mono text-xs"
                />
              </FieldRow>
            )}
          </Group>
        </Section>

        {/* ------------------------------------------------------------ 2. techniques */}
        <Section
          n={2}
          title={t('setup.step.techniques')}
          badge={String(draft.techniques.length)}
          aside={
            <>
              <Button
                variant="ghost"
                size="xs"
                onClick={() =>
                  set(
                    'techniques',
                    techniques.map((x) => x.name)
                  )
                }
              >
                {t('setup.tech.all')}
              </Button>
              <Button
                variant="ghost"
                size="xs"
                onClick={() =>
                  set(
                    'techniques',
                    techniques.filter((x) => x.status === 'implemented').map((x) => x.name)
                  )
                }
              >
                {t('setup.tech.implemented')}
              </Button>
              <Button variant="ghost" size="xs" onClick={() => set('techniques', [])}>
                {t('setup.tech.none')}
              </Button>
            </>
          }
        >
          <p className="text-[11px] text-muted-foreground">{t('setup.tech.paramsHint')}</p>
          <ul className="flex max-h-[calc(100svh-21rem)] min-h-64 flex-col gap-1 overflow-auto pr-1">
            {byStage.map((tech, position) => {
              const on = draft.techniques.includes(tech.name)
              const params = Object.entries(tech.params)
              const needs = tech.requires.filter((r) => r in INDEX_NEEDS)
              const firstOfStage = position === 0 || byStage[position - 1].stage !== tech.stage
              return (
                <Fragment key={tech.name}>
                  {firstOfStage && (
                    <li className="sticky top-0 z-10 flex items-baseline justify-between gap-2 border-b bg-card px-1 pt-2 pb-1 text-[11px] font-semibold tracking-wide uppercase">
                      <span>{gt(stageKey(tech.stage))}</span>
                      <span className="font-mono font-normal text-muted-foreground">
                        {
                          byStage.filter(
                            (x) => x.stage === tech.stage && draft.techniques.includes(x.name)
                          ).length
                        }
                        /{byStage.filter((x) => x.stage === tech.stage).length}
                      </span>
                    </li>
                  )}
                  <li
                    className={cn(
                      'rounded-md border px-2 py-1.5',
                      on ? 'bg-muted/40' : 'border-transparent'
                    )}
                  >
                    <label className="flex cursor-pointer items-start gap-2">
                      <Checkbox
                        checked={on}
                        onCheckedChange={(c) => toggleTechnique(tech.name, c === true)}
                        className="mt-0.5"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-1.5">
                          <span className="text-sm font-medium">{tech.title || tech.name}</span>
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {tech.name}
                          </span>
                          {tech.status !== 'implemented' && (
                            <TechniqueStatusBadge status={tech.status} label={tech.status} />
                          )}
                          {tech.ignores.length > 0 && (
                            <span
                              className="rounded border border-dashed px-1 text-[10px] text-muted-foreground"
                              title={t('setup.tech.ignoresHint')}
                            >
                              {t('setup.tech.ignores', {
                                axes: tech.ignores.map((a) => gt(axisKey(a))).join(', ')
                              })}
                            </span>
                          )}
                          {needs.map((need) => (
                            <span
                              key={need}
                              className="rounded border border-amber-500/60 px-1 text-[10px] text-amber-700 dark:text-amber-400"
                              title={t('setup.tech.needsHint')}
                            >
                              {t(INDEX_NEEDS[need])}
                            </span>
                          ))}
                        </span>
                        <span className="block text-[11px] leading-snug text-muted-foreground">
                          {tech.description}
                        </span>
                      </span>
                    </label>
                    {on && params.length > 0 && (
                      <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1.5 pl-6 2xl:grid-cols-3">
                        {params.map(([param, fallback]) => (
                          <label key={param} className="flex min-w-0 flex-col gap-0.5">
                            <span className="truncate font-mono text-[11px] text-muted-foreground">
                              {param}
                            </span>
                            <Input
                              value={draft.params[tech.name]?.[param] ?? ''}
                              placeholder={fallback === null ? '∅' : String(fallback)}
                              onChange={(e) => setParam(tech.name, param, e.target.value)}
                              className="h-7 font-mono text-xs"
                            />
                          </label>
                        ))}
                      </div>
                    )}
                  </li>
                </Fragment>
              )
            })}
          </ul>
        </Section>

        {/* ------------------------------------------------------------------ 3. grid */}
        <Section n={3} title={t('setup.step.grid')} className="md:col-span-2 xl:col-span-1">
          <Group title={t('setup.group.index')}>
            <div className="flex flex-col gap-1.5">
              {draft.chunking.map((row, i) => (
                <div key={i} className="flex items-end gap-1.5">
                  <FieldRow label={i === 0 ? t('setup.chunking.strategy') : ''} className="flex-1">
                    <Select
                      value={row.strategy}
                      onValueChange={(v) => setChunk(i, { strategy: v })}
                    >
                      <SelectTrigger size="sm" className="w-full font-mono text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STRATEGIES.map((s) => (
                          <SelectItem key={s} value={s}>
                            {s}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FieldRow>
                  <FieldRow label={i === 0 ? t('setup.chunking.size') : ''} className="w-20">
                    <Input
                      value={row.size}
                      onChange={(e) => setChunk(i, { size: e.target.value })}
                      className="h-7 font-mono text-xs"
                    />
                  </FieldRow>
                  <FieldRow label={i === 0 ? t('setup.chunking.overlap') : ''} className="w-20">
                    <Input
                      value={row.overlap}
                      onChange={(e) => setChunk(i, { overlap: e.target.value })}
                      className="h-7 font-mono text-xs"
                    />
                  </FieldRow>
                  {row.strategy === 'parent_child' && (
                    <FieldRow label={i === 0 ? t('setup.chunking.parent') : ''} className="w-20">
                      <Input
                        value={row.parent}
                        onChange={(e) => setChunk(i, { parent: e.target.value })}
                        className="h-7 font-mono text-xs"
                      />
                    </FieldRow>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="remove"
                    disabled={draft.chunking.length === 1}
                    onClick={() =>
                      set(
                        'chunking',
                        draft.chunking.filter((_, j) => j !== i)
                      )
                    }
                  >
                    <X />
                  </Button>
                </div>
              ))}
              <Button
                variant="outline"
                size="xs"
                className="w-fit"
                onClick={() =>
                  set('chunking', [
                    ...draft.chunking,
                    { strategy: 'fixed', size: '500', overlap: '80', parent: '1500' }
                  ])
                }
              >
                <Plus /> {t('setup.chunking.add')}
              </Button>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_8rem] gap-2">
              <FieldRow label={t('setup.enrich')}>
                <ToggleChips
                  options={[
                    { value: 'none', label: t('setup.enrich.none') },
                    { value: 'contextual' }
                  ]}
                  value={draft.enrich}
                  onChange={(v) => set('enrich', v)}
                  min={1}
                />
              </FieldRow>
              <FieldRow label={t('setup.store')}>
                <Select value={draft.store} onValueChange={(v) => set('store', v)}>
                  <SelectTrigger size="sm" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STORES.map((s) => (
                      <SelectItem key={s} value={s} disabled={Boolean(missing.stores[s])}>
                        {s}
                        {missing.stores[s] && (
                          <span className="text-muted-foreground">
                            {t('setup.needs', { pkg: missing.stores[s] })}
                          </span>
                        )}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldRow>
            </div>
          </Group>

          <Group title={t('setup.group.retrieval')}>
            <FieldRow label={t('setup.modes')}>
              <ToggleChips
                options={MODES.map((m) => ({ value: m }))}
                value={draft.modes}
                onChange={(v) => set('modes', v)}
                min={1}
              />
            </FieldRow>
            <FieldRow label={t('setup.rerankers')}>
              <ToggleChips
                options={RERANKERS.map((m) => ({
                  value: m,
                  disabled: Boolean(missing.rerankers[m]),
                  hint: missing.rerankers[m]
                    ? t('setup.needsHint', { pkg: missing.rerankers[m] })
                    : undefined
                }))}
                value={draft.rerankers}
                onChange={(v) => set('rerankers', v)}
                min={1}
              />
              {draft.rerankers.some((r) => missing.rerankers[r]) && (
                <p className="text-[11px] text-destructive">
                  {t('setup.needsHint', {
                    pkg: draft.rerankers
                      .map((r) => missing.rerankers[r])
                      .filter(Boolean)
                      .join(', ')
                  })}
                </p>
              )}
              {draft.store === 'faiss' && draft.rerankers.includes('cross_encoder') && (
                <p className="text-[11px] text-destructive">{t('setup.faissCross')}</p>
              )}
            </FieldRow>
            <div className="grid grid-cols-2 gap-2">
              <FieldRow label={t('setup.k')}>
                <Input
                  value={draft.k}
                  onChange={(e) => set('k', e.target.value)}
                  className="font-mono"
                />
              </FieldRow>
              <FieldRow label={t('setup.seeds')}>
                <Input
                  value={draft.seeds}
                  onChange={(e) => set('seeds', e.target.value)}
                  className="font-mono"
                />
              </FieldRow>
            </div>
          </Group>

          <Group title={t('setup.group.models')}>
            <div className="grid grid-cols-2 gap-2">
              <FieldRow label={t('setup.llms')}>
                <Input
                  value={draft.llms}
                  placeholder={defaultLlm}
                  title={t('setup.modelHint')}
                  onChange={(e) => set('llms', e.target.value)}
                  className="font-mono text-xs"
                />
              </FieldRow>
              <FieldRow label={t('setup.embeddings')}>
                <Input
                  value={draft.embeddings}
                  placeholder={defaultEmbedding}
                  title={t('setup.modelHint')}
                  onChange={(e) => set('embeddings', e.target.value)}
                  className="font-mono text-xs"
                />
              </FieldRow>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <FieldRow label={t('setup.language')}>
                <Select value={draft.language} onValueChange={(v) => set('language', v)}>
                  <SelectTrigger size="sm" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pt">pt</SelectItem>
                    <SelectItem value="en">en</SelectItem>
                  </SelectContent>
                </Select>
              </FieldRow>
              <FieldRow label={t('setup.maxContext')}>
                <Input
                  value={draft.maxContext}
                  onChange={(e) => set('maxContext', e.target.value)}
                  className="h-7 font-mono text-xs"
                />
              </FieldRow>
              <FieldRow label={t('setup.temperature')}>
                <Input
                  value={draft.temperature}
                  onChange={(e) => set('temperature', e.target.value)}
                  className="h-7 font-mono text-xs"
                />
              </FieldRow>
            </div>
          </Group>
        </Section>
      </div>

      {/* ------------------------------------------------------------- sticky review */}
      <div className="sticky bottom-0 z-10 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border bg-card px-3 py-2 shadow-md">
        <Figure
          label={t('review.runs')}
          value={
            fresh
              ? String(preview.data.runs)
              : built.ok
                ? `${mayPrune ? '≤ ' : ''}${built.runs}`
                : '–'
          }
        />
        <Figure
          label={t('review.answers')}
          value={
            est
              ? est.answers.toLocaleString()
              : built.ok && typeof questionCount === 'number'
                ? `≈ ${(built.runs * questionCount).toLocaleString()}`
                : '–'
          }
        />
        <Figure
          label={t('review.tokens')}
          value={est ? (est.prompt_tokens + est.completion_tokens).toLocaleString() : '–'}
        />
        <Figure
          label={t('review.cost')}
          value={
            est
              ? est.cost_usd === null
                ? t('review.costUnknown')
                : fmtMetric('cost_usd', est.cost_usd)
              : '–'
          }
        />
        <div className="min-w-0 flex-1 text-xs">
          {localError || serverError ? (
            <span className="flex items-start gap-1.5 text-destructive">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
              <span className="line-clamp-2" title={serverError ?? undefined}>
                {localError ?? serverError}
              </span>
            </span>
          ) : (
            <span className="line-clamp-2 text-muted-foreground" title={prunedNote || undefined}>
              {fresh
                ? `${prunedNote ? `${prunedNote} ` : ''}${t('review.lowerBound')}`
                : preview
                  ? t('review.stale')
                  : t('review.needPreview')}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={!built.ok || busy !== null}
            onClick={() => void runPreview()}
          >
            {busy === 'preview' ? <LoaderCircle className="animate-spin" /> : <Eye />}
            {t('review.preview')}
          </Button>
          <Button
            variant="outline"
            disabled={!built.ok || busy !== null}
            onClick={() => void create(false)}
          >
            {busy === 'create' ? <LoaderCircle className="animate-spin" /> : <Save />}
            {t('review.create')}
          </Button>
          <Button disabled={!built.ok || busy !== null} onClick={() => void create(true)}>
            {busy === 'run' ? <LoaderCircle className="animate-spin" /> : <Play />}
            {t('review.createRun')}
          </Button>
        </div>
      </div>
    </div>
  )
}

function Figure({ label, value }: { label: string; value: string }): React.JSX.Element {
  return (
    <div className="flex flex-col">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className="font-mono text-sm font-semibold tabular-nums">{value}</span>
    </div>
  )
}
