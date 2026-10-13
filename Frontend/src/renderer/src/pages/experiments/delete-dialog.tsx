import { useCallback, useState } from 'react'
import { LoaderCircle, TriangleAlert } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type { RunbookSummary } from '@/lib/types'
import type { ExpKey } from './i18n'

/** Guarded deletion: the exact runbook name must be typed; the backend backs the database up first. */
export function DeleteRunbookDialog({
  t,
  runbook,
  onClose,
  onDeleted
}: {
  t: PageT<ExpKey>
  runbook: RunbookSummary
  onClose: () => void
  onDeleted: (id: string) => void
}): React.JSX.Element {
  const gt = useT()
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const preview = useApiData(
    useCallback(() => api.experiments.deletePreview(runbook.id), [runbook.id])
  )

  const remove = async (): Promise<void> => {
    setBusy(true)
    const res = await api.experiments.delete(runbook.id, typed)
    setBusy(false)
    if (!res.ok) return void toast.error(res.error)
    toast.success(t('delete.done', { path: res.data.backup }))
    onDeleted(runbook.id)
    onClose()
  }

  return (
    <Dialog open onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TriangleAlert className="size-4 text-destructive" /> {t('delete.title')}
          </DialogTitle>
          <DialogDescription>{t('delete.description')}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 text-sm">
          <div className="rounded-md border bg-muted/40 p-2">
            <div className="font-medium">{runbook.name}</div>
            <div className="font-mono text-xs text-muted-foreground">{runbook.id}</div>
            {preview.data && (
              <div className="mt-1 text-xs">
                {t('delete.preview', {
                  runs: preview.data.runs,
                  results: preview.data.query_results,
                  events: preview.data.evidence_events
                })}
              </div>
            )}
          </div>
          <label className="text-xs" htmlFor="confirm-name">
            {t('delete.confirm')}
          </label>
          <Input
            id="confirm-name"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder={runbook.name}
            autoComplete="off"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            {gt('common.cancel')}
          </Button>
          <Button
            variant="destructive"
            disabled={busy || typed !== runbook.name}
            onClick={() => void remove()}
          >
            {busy && <LoaderCircle className="animate-spin" />}
            {gt('common.delete')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
