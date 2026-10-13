import { ArrowDown, ArrowUp, ExternalLink, FileText, Scale, TriangleAlert } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import type { PageT } from '@/components/shared/use-page-t'
import type { ReferenceCatalog, ReferenceEntry, ReferenceSource } from '@/lib/types'
import { cn } from '@/lib/utils'
import { TechniqueStatusBadge } from '@/pages/techniques/status-badge'
import type { RefKey } from './i18n'

type T = PageT<RefKey>

const MONO_KINDS = new Set(['component'])

function Fact({
  label,
  children
}: {
  label: string
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-1.5 text-sm">{children}</div>
    </div>
  )
}

function Code({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
}

function Facts({
  entry,
  catalog,
  t
}: {
  entry: ReferenceEntry
  catalog: ReferenceCatalog
  t: T
}): React.JSX.Element | null {
  const f = entry.facts
  const items: React.ReactNode[] = []
  if (f.identifier)
    items.push(
      <Fact key="identifier" label={t('facts.identifier')}>
        <Code>{f.identifier}</Code>
      </Fact>
    )
  if (f.status)
    items.push(
      <Fact key="status" label={t('facts.status')}>
        <TechniqueStatusBadge status={f.status} label={t(`status.${f.status}` as RefKey)} />
        {f.version && <span className="font-mono text-xs text-muted-foreground">v{f.version}</span>}
      </Fact>
    )
  if (f.family)
    items.push(
      <Fact key="family" label={t('facts.family')}>
        {catalog.groups[`family:${f.family}`] ?? f.family}
      </Fact>
    )
  if (f.ignores?.length)
    items.push(
      <Fact key="ignores" label={t('facts.ignores')}>
        {f.ignores.map((axis) => (
          <Code key={axis}>{axis}</Code>
        ))}
      </Fact>
    )
  if (f.calls)
    items.push(
      <Fact key="calls" label={t('facts.calls')}>
        <span className="font-mono">{f.calls}</span>
      </Fact>
    )
  if (f.requires?.length)
    items.push(
      <Fact key="requires" label={t('facts.requires')}>
        {f.requires.map((r) => (
          <Code key={r}>{r}</Code>
        ))}
      </Fact>
    )
  if (f.needs)
    items.push(
      <Fact key="needs" label={t('facts.needs')}>
        <Badge variant={f.needs === 'none' ? 'secondary' : 'outline'}>
          {t(`needs.${f.needs}` as RefKey)}
        </Badge>
      </Fact>
    )
  if (f.better) {
    const Icon = f.better === 'higher' ? ArrowUp : f.better === 'lower' ? ArrowDown : Scale
    items.push(
      <Fact key="better" label={t('facts.better')}>
        <Icon className="size-3.5 text-muted-foreground" aria-hidden />
        {t(`better.${f.better}` as RefKey)}
      </Fact>
    )
  }
  if (f.range)
    items.push(
      <Fact key="range" label={t('facts.range')}>
        {t(`range.${f.range}` as RefKey)}
      </Fact>
    )
  if (f.keys?.length)
    items.push(
      <Fact key="keys" label={t('facts.keys')}>
        {f.keys.map((k) => (
          <Code key={k}>{k}</Code>
        ))}
      </Fact>
    )
  if (f.package)
    items.push(
      <Fact key="package" label={t('facts.package')}>
        <Code>pip install {f.package}</Code>
      </Fact>
    )
  if (items.length === 0) return null
  return (
    <div className="flex flex-wrap gap-x-8 gap-y-3 rounded-lg border bg-muted/30 px-4 py-3">
      {items}
    </div>
  )
}

function Steps({ text }: { text: string }): React.JSX.Element {
  const lines = text.split('\n').filter((l) => l.trim())
  const numbered = lines.every((l) => /^\d+\.\s/.test(l))
  const List = numbered ? 'ol' : 'ul'
  return (
    <List className={cn('flex flex-col gap-1.5 pl-5', numbered ? 'list-decimal' : 'list-disc')}>
      {lines.map((line) => (
        <li key={line} className="pl-1 marker:text-muted-foreground">
          {numbered ? line.replace(/^\d+\.\s/, '') : line}
        </li>
      ))}
    </List>
  )
}

function Params({ entry, t }: { entry: ReferenceEntry; t: T }): React.JSX.Element | null {
  const params = entry.facts.params
  if (!params) return null
  return (
    <section className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold">{t('params.title')}</h4>
      {params.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('params.none')}</p>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('params.name')}</TableHead>
                  <TableHead>{t('params.default')}</TableHead>
                  <TableHead>{t('params.help')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {params.map((p) => (
                  <TableRow key={p.name}>
                    <TableCell className="font-mono text-xs">{p.name}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {p.default === null ? '∅' : String(p.default)}
                    </TableCell>
                    <TableCell className="text-xs whitespace-normal text-muted-foreground">
                      {p.help || '–'}
                      {p.choices && (
                        <span className="ml-1 font-mono">
                          ({p.choices.map(String).join(' | ')})
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground">{t('params.hint')}</p>
        </>
      )}
    </section>
  )
}

export function SourceLine({ source, t }: { source: ReferenceSource; t: T }): React.JSX.Element {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border px-3 py-2">
      <div className="min-w-0 text-sm">
        <p className="leading-snug font-medium">{source.title}</p>
        <p className="text-xs text-muted-foreground">
          {[source.authors, source.venue, source.year].filter(Boolean).join(' · ')}
        </p>
        {source.checked === null && (
          <p
            className="mt-1 inline-flex items-center gap-1 text-xs text-amber-700 dark:text-amber-400"
            title={t('sources.uncheckedHint')}
          >
            <TriangleAlert className="size-3" aria-hidden /> {t('sources.unchecked')}
          </p>
        )}
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          title={
            source.checked
              ? `${source.url}\n${t('sources.checked', { date: source.checked })}`
              : source.url
          }
        >
          <ExternalLink /> {t('sources.open')}
        </a>
      </Button>
    </div>
  )
}

async function openProjectFile(file: string): Promise<void> {
  try {
    const { projectRoot } = await window.api.getPaths()
    await window.api.openPath(`${projectRoot}/${file}`)
  } catch (e) {
    toast.error((e as Error).message)
  }
}

export function EntryDetail({
  entry,
  catalog,
  t,
  onNavigate
}: {
  entry: ReferenceEntry
  catalog: ReferenceCatalog
  t: T
  onNavigate: (id: string) => void
}): React.JSX.Element {
  const related = entry.related
    .map((id) => catalog.entries.find((e) => e.id === id))
    .filter((e): e is ReferenceEntry => Boolean(e))
  const sources = entry.sources.map((key) => catalog.sources[key]).filter(Boolean)
  return (
    <article className="flex flex-col gap-5">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline">{t(`kind.${entry.kind}` as RefKey)}</Badge>
          <span>{catalog.groups[entry.group] ?? entry.group}</span>
        </div>
        <h3
          className={cn(
            'text-xl font-semibold tracking-tight',
            MONO_KINDS.has(entry.kind) && 'font-mono'
          )}
        >
          {entry.name}
        </h3>
        <p className="max-w-3xl text-base leading-relaxed">{entry.summary}</p>
      </header>

      <Facts entry={entry} catalog={catalog} t={t} />

      <div className="grid gap-x-8 gap-y-5 xl:grid-cols-2">
        {entry.sections.map((section) => {
          const specific = `section.${section.key}.${entry.kind}` as RefKey
          const title =
            t(specific) === specific ? t(`section.${section.key}` as RefKey) : t(specific)
          return (
            <section
              key={section.key}
              className={cn('flex flex-col gap-1.5', section.key === 'steps' && 'xl:col-span-2')}
            >
              <h4 className="text-sm font-semibold">{title}</h4>
              <div className="text-sm leading-relaxed text-foreground/90">
                {section.key === 'steps' ? <Steps text={section.text} /> : <p>{section.text}</p>}
              </div>
            </section>
          )
        })}
      </div>

      {entry.facts.files && (
        <div className="flex flex-wrap gap-2">
          {entry.facts.files.map((file) => (
            <Button
              key={file}
              variant="outline"
              size="sm"
              title={t('docs.open')}
              onClick={() => void openProjectFile(file)}
            >
              <FileText /> {file}
            </Button>
          ))}
        </div>
      )}

      <Params entry={entry} t={t} />

      <section className="flex flex-col gap-2">
        <h4 className="text-sm font-semibold">{t('sources.title')}</h4>
        {sources.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('sources.none')}</p>
        ) : (
          <div className="grid gap-2 xl:grid-cols-2">
            {sources.map((source) => (
              <SourceLine key={source.url} source={source} t={t} />
            ))}
          </div>
        )}
      </section>

      {related.length > 0 && (
        <section className="flex flex-col gap-2">
          <h4 className="text-sm font-semibold">{t('related.title')}</h4>
          <div className="flex flex-wrap gap-1.5">
            {related.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => onNavigate(r.id)}
                title={r.summary}
                className="inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-xs transition-colors outline-none hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
              >
                <span className="text-muted-foreground">{t(`kind.${r.kind}` as RefKey)}</span>
                <span className={cn('font-medium', MONO_KINDS.has(r.kind) && 'font-mono')}>
                  {r.name}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}
    </article>
  )
}
