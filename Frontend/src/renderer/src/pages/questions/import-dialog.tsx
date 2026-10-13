import { useState } from 'react'
import { FileJson, LoaderCircle } from 'lucide-react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { ErrorAlert } from '@/components/shared/error-alert'
import { FieldRow } from '@/components/shared/field-row'
import type { PageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type { CorpusSummary } from '@/lib/types'
import type { QKey } from './i18n'

export function ImportDialog({
  t,
  open,
  onOpenChange,
  corpora,
  onImported
}: {
  t: PageT<QKey>
  open: boolean
  onOpenChange: (open: boolean) => void
  corpora: CorpusSummary[]
  onImported: (setName: string) => void
}): React.JSX.Element {
  const gt = useT()
  const [path, setPath] = useState('')
  const [corpus, setCorpus] = useState<string>('')
  const [setName, setSetName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const corpusValue = corpus || corpora[0]?.name || 'none'

  const choose = async (): Promise<void> => {
    const files = await window.api.openFiles([{ name: 'JSON', extensions: ['json'] }])
    if (files[0]) setPath(files[0])
  }

  const submit = async (): Promise<void> => {
    setBusy(true)
    setError(null)
    const res = await api.questions.importJson(
      path,
      corpusValue === 'none' ? undefined : corpusValue,
      setName.trim() || undefined
    )
    setBusy(false)
    if (!res.ok) return setError(res.error)
    for (const w of res.warnings ?? []) toast.warning(w)
    toast.success(t('import.done', { n: res.data.questions }))
    onImported(res.data.name)
    onOpenChange(false)
    setPath('')
    setSetName('')
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{t('import.title')}</DialogTitle>
          <DialogDescription>{t('import.description')}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <FieldRow label={t('import.file')}>
            <div className="flex gap-1.5">
              <Input
                value={path}
                onChange={(e) => setPath(e.target.value)}
                className="font-mono text-xs"
              />
              <Button variant="outline" onClick={() => void choose()}>
                <FileJson /> {t('import.choose')}
              </Button>
            </div>
          </FieldRow>
          <div className="grid gap-3 sm:grid-cols-2">
            <FieldRow label={t('import.corpus')}>
              <Select value={corpusValue} onValueChange={setCorpus}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t('import.noCorpus')}</SelectItem>
                  {corpora.map((c) => (
                    <SelectItem key={c.id} value={c.name}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldRow>
            <FieldRow label={t('import.set')} help={t('import.setHint')}>
              <Input value={setName} onChange={(e) => setSetName(e.target.value)} />
            </FieldRow>
          </div>
        </div>
        <ErrorAlert title={gt('common.error')} message={error} />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            {gt('common.cancel')}
          </Button>
          <Button onClick={() => void submit()} disabled={busy || !path.trim()}>
            {busy && <LoaderCircle className="animate-spin" />}
            {t('import.run')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
