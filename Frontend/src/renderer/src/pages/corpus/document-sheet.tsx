import { useMemo } from 'react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle
} from '@/components/ui/sheet'
import { ErrorAlert } from '@/components/shared/error-alert'
import { JsonView } from '@/components/shared/json-view'
import { LoadingState } from '@/components/shared/loading-state'
import { Stat } from '@/components/shared/stat'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type { DocumentDetail } from '@/lib/types'
import type { CorpusKey } from './i18n'

export function DocumentSheet({
  t,
  corpus,
  docId,
  onClose
}: {
  t: PageT<CorpusKey>
  corpus: string
  docId: string | null
  onClose: () => void
}): React.JSX.Element {
  const gt = useT()
  const doc = useApiData<DocumentDetail>(
    useMemo(() => (docId ? () => api.corpus.document(corpus, docId) : null), [corpus, docId])
  )
  const d = docId ? doc.data : null
  const p = d?.profile
  return (
    <Sheet open={docId !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 sm:max-w-4xl">
        <SheetHeader>
          <SheetTitle className="font-mono">{docId}</SheetTitle>
          <SheetDescription className="truncate font-mono text-xs">
            {d?.source_path ?? ''}
          </SheetDescription>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-auto px-4 pb-4">
          <ErrorAlert title={gt('common.error')} message={docId ? doc.error : null} />
          {doc.loading && !d && <LoadingState rows={6} />}
          {d && p && (
            <>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-6">
                <Stat label={t('docs.chars')} value={p.chars.toLocaleString()} mono />
                <Stat label={t('docs.words')} value={p.words.toLocaleString()} mono />
                <Stat label={t('docs.paragraphs')} value={p.paragraphs} mono />
                <Stat label={t('docs.headings')} value={p.headings} mono />
                <Stat label={t('docs.language')} value={p.language} mono />
                <Stat label={t('docs.format')} value={p.format} mono />
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="outline" className="font-mono">
                  sha256 {d.sha256.slice(0, 16)}…
                </Badge>
                <span>{t('sheet.textHint')}</span>
              </div>
              {Object.keys(d.metadata ?? {}).length > 0 && (
                <div>
                  <div className="mb-1 text-xs font-medium">{t('sheet.metadata')}</div>
                  <JsonView value={d.metadata} maxHeight="max-h-32" />
                </div>
              )}
              <div className="min-h-0 flex-1">
                <div className="mb-1 text-xs font-medium">{t('sheet.text')}</div>
                <pre className="max-h-[60vh] overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
                  {d.text}
                </pre>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
