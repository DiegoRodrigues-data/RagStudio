import { ExternalLink, TriangleAlert } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { EmptyState } from '@/components/shared/empty-state'
import type { PageT } from '@/components/shared/use-page-t'
import type { RefKey } from './i18n'
import type { SourceRow } from './lookup'

/** Every source the catalog cites, with the entries that cite it. */
export function SourcesView({
  rows,
  t,
  onNavigate
}: {
  rows: SourceRow[]
  t: PageT<RefKey>
  onNavigate: (id: string) => void
}): React.JSX.Element {
  if (rows.length === 0) return <EmptyState title={t('empty.sources')} />
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <p className="text-xs text-muted-foreground">
        {t('sources.summary', {
          n: rows.length,
          checked: rows.filter((r) => r.source.checked !== null).length
        })}
      </p>
      <div className="min-h-0 flex-1 overflow-auto rounded-lg border">
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-background">
            <TableRow>
              <TableHead className="w-56">{t('sources.col.source')}</TableHead>
              <TableHead>{t('sources.col.title')}</TableHead>
              <TableHead className="w-[34%]">{t('sources.col.usedBy')}</TableHead>
              <TableHead className="w-44">{t('sources.col.link')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(({ key, source, usedBy }) => (
              <TableRow key={key} className="align-top">
                <TableCell className="text-sm whitespace-normal">
                  <span className="font-medium">{source.authors || '–'}</span>
                  {source.year && <span className="text-muted-foreground"> · {source.year}</span>}
                </TableCell>
                <TableCell className="text-sm whitespace-normal">
                  <p className="leading-snug">{source.title}</p>
                  <p className="text-xs text-muted-foreground">{source.venue}</p>
                </TableCell>
                <TableCell className="whitespace-normal">
                  <div className="flex flex-wrap gap-1">
                    {usedBy.map((entry) => (
                      <button
                        key={entry.id}
                        type="button"
                        onClick={() => onNavigate(entry.id)}
                        className="rounded border px-1.5 py-0.5 text-xs transition-colors outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring/50"
                      >
                        {entry.name}
                      </button>
                    ))}
                  </div>
                </TableCell>
                <TableCell className="text-xs whitespace-normal">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    title={source.url}
                    className="inline-flex items-center gap-1 text-primary underline-offset-4 hover:underline"
                  >
                    <ExternalLink className="size-3" />
                    {new URL(source.url).hostname.replace('www.', '')}
                  </a>
                  {source.checked === null && (
                    <p
                      className="mt-1 flex items-center gap-1 text-amber-700 dark:text-amber-400"
                      title={t('sources.uncheckedHint')}
                    >
                      <TriangleAlert className="size-3" aria-hidden /> {t('sources.unchecked')}
                    </p>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
