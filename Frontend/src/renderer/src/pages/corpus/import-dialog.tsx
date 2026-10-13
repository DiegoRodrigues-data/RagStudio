import { useState } from 'react'
import { FileText, FolderOpen, LoaderCircle } from 'lucide-react'
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
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { ToggleChips } from '@/components/shared/chips'
import { ErrorAlert } from '@/components/shared/error-alert'
import { FieldRow } from '@/components/shared/field-row'
import type { PageT } from '@/components/shared/use-page-t'
import { useStream } from '@/hooks/use-stream'
import { useStreamDone } from '@/hooks/use-stream-done'
import { useT } from '@/hooks/use-t'
import type { ProgressEvent } from '@/lib/types'
import type { CorpusKey } from './i18n'

const FLAGS = [
  'remove_image_tags',
  'remove_repeated_headers',
  'collapse_blank_lines',
  'remove_print_metadata'
] as const
type Flag = (typeof FLAGS)[number]

function baseName(path: string): string {
  const last =
    path
      .replace(/[\\/]+$/, '')
      .split(/[\\/]/)
      .pop() ?? ''
  return last.replace(/\.[^.]+$/, '')
}

export function ImportDialog({
  t,
  open,
  onOpenChange,
  onImported
}: {
  t: PageT<CorpusKey>
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported: (name: string) => void
}): React.JSX.Element {
  const gt = useT()
  const [path, setPath] = useState('')
  const [name, setName] = useState('')
  const [language, setLanguage] = useState('auto')
  const [description, setDescription] = useState('')
  const [flags, setFlags] = useState<Flag[]>([])
  const [error, setError] = useState<string | null>(null)
  const job = useStream<ProgressEvent>()
  const busy = job.running

  const pick = (p: string | null | undefined): void => {
    if (!p) return
    setPath(p)
    if (!name.trim()) setName(baseName(p))
  }

  const chooseFile = async (): Promise<void> => {
    const files = await window.api.openFiles([
      { name: 'Documents', extensions: ['md', 'markdown', 'txt', 'json', 'jsonl', 'pdf'] }
    ])
    pick(files[0])
  }

  useStreamDone(job, (done) => {
    const res = done.result
    if (!res) return setError(done.error ?? (done.code === null ? t('import.cancelled') : 'error'))
    if (!res.ok) return setError(res.error)
    const data = res.data as { name: string; documents: number; skipped?: number }
    const warnings = res.warnings ?? []
    if (warnings.length > 0)
      toast.warning(t('import.skipped', { n: warnings.length }), {
        description: warnings.slice(0, 3).join('\n')
      })
    toast.success(t('import.done', { n: data.documents }))
    onImported(data.name)
    onOpenChange(false)
    setPath('')
    setName('')
    setDescription('')
    setFlags([])
  })

  const submit = (): void => {
    setError(null)
    void job.startWith((id) =>
      api.corpus.import(id, {
        path,
        name: name.trim(),
        language: language === 'auto' ? undefined : language,
        description: description.trim() || undefined,
        clean: flags.join(',') || undefined
      })
    )
  }

  const last = job.lastEvent?.progress
  const pct = last && last.total ? ((last.done ?? 0) / last.total) * 100 : 0
  const failed = job.events.filter((e) => e.progress?.event === 'file' && e.progress.ok === false)

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('import.title')}</DialogTitle>
          <DialogDescription>{t('import.description')}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <FieldRow label={t('import.path')} help={t('import.pdfHint')} className="sm:col-span-2">
            <div className="flex gap-1.5">
              <Input
                value={path}
                onChange={(e) => setPath(e.target.value)}
                className="font-mono text-xs"
              />
              <Button variant="outline" onClick={() => void window.api.openDirectory().then(pick)}>
                <FolderOpen /> {t('import.chooseFolder')}
              </Button>
              <Button variant="outline" onClick={() => void chooseFile()}>
                <FileText /> {t('import.chooseFile')}
              </Button>
            </div>
          </FieldRow>
          <FieldRow label={t('import.name')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </FieldRow>
          <FieldRow label={t('import.language')}>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">{t('import.auto')}</SelectItem>
                <SelectItem value="pt">pt</SelectItem>
                <SelectItem value="en">en</SelectItem>
              </SelectContent>
            </Select>
          </FieldRow>
          <FieldRow label={t('import.descriptionField')} className="sm:col-span-2">
            <Input value={description} onChange={(e) => setDescription(e.target.value)} />
          </FieldRow>
          <FieldRow label={t('import.clean')} className="sm:col-span-2">
            <ToggleChips
              options={FLAGS.map((f) => ({ value: f, label: t(`import.clean.${f}`) }))}
              value={flags}
              onChange={setFlags}
            />
          </FieldRow>
        </div>
        {busy && (
          <div className="flex flex-col gap-1">
            <Progress value={pct} />
            <span className="truncate font-mono text-[11px] text-muted-foreground">
              {last
                ? `${last.done ?? 0}/${last.total ?? '?'} · ${last.name ?? ''}${failed.length > 0 ? ` · ${t('import.failedCount', { n: failed.length })}` : ''}`
                : t('import.starting')}
            </span>
          </div>
        )}
        <ErrorAlert title={gt('common.error')} message={error} />
        <DialogFooter>
          {busy ? (
            <Button variant="destructive" onClick={() => void job.cancel()}>
              {t('import.cancel')}
            </Button>
          ) : (
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {gt('common.cancel')}
            </Button>
          )}
          <Button onClick={submit} disabled={busy || !path.trim() || !name.trim()}>
            {busy && <LoaderCircle className="animate-spin" />}
            {t('import.run')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
