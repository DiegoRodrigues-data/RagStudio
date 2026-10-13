import { useMemo, useState } from 'react'
import { LoaderCircle, Plus, X } from 'lucide-react'
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
import { Textarea } from '@/components/ui/textarea'
import { ErrorAlert } from '@/components/shared/error-alert'
import { FieldRow } from '@/components/shared/field-row'
import { useApiData } from '@/components/shared/use-api-data'
import type { PageT } from '@/components/shared/use-page-t'
import { useT } from '@/hooks/use-t'
import type { CorpusDetail, CorpusSummary, Question } from '@/lib/types'
import type { QKey } from './i18n'

const TYPES = ['extraction', 'boolean', 'classification', 'reasoning', 'summarization']
const SPLITS = ['train', 'validation', 'test']

interface Gold {
  document_id: string
  text: string
}

export interface QuestionDialogRequest {
  /** Existing question to edit, or null to create. */
  question: Question | null
  setName: string
}

export function QuestionDialog({
  t,
  request,
  corpora,
  onClose,
  onSaved
}: {
  t: PageT<QKey>
  request: QuestionDialogRequest
  corpora: CorpusSummary[]
  onClose: () => void
  onSaved: (setName: string) => void
}): React.JSX.Element {
  const gt = useT()
  const q = request.question
  const [setName, setSetName] = useState(request.setName)
  const [code, setCode] = useState(q?.code ?? '')
  const [text, setText] = useState(q?.text ?? '')
  const [expected, setExpected] = useState(q?.expected_answer ?? '')
  const [type, setType] = useState(q?.answer_type ?? 'extraction')
  const [split, setSplit] = useState(q?.split ?? 'none')
  const [corpus, setCorpus] = useState('')
  const [gold, setGold] = useState<Gold[]>(
    (q?.gold_passages ?? []).map((g) => ({ document_id: g.document_id, text: g.text }))
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const corpusValue = corpus || corpora[0]?.name || ''
  const detail = useApiData<CorpusDetail>(
    useMemo(() => (corpusValue ? () => api.corpus.describe(corpusValue) : null), [corpusValue])
  )
  const documents = detail.data?.documents.map((d) => d.doc_id) ?? []
  const goldClean = gold.filter((g) => g.document_id && g.text.trim())

  const submit = async (): Promise<void> => {
    if (goldClean.length > 0 && !corpusValue) return setError(t('dialog.needCorpus'))
    setBusy(true)
    setError(null)
    const common = {
      text: text.trim(),
      expectedAnswer: expected.trim() || undefined,
      answerType: type,
      split: split === 'none' ? undefined : split,
      goldPassages: goldClean.length > 0 || q ? goldClean : undefined,
      corpus: goldClean.length > 0 ? corpusValue : undefined
    }
    const res = q
      ? await api.questions.update({ id: q.id, ...common })
      : await api.questions.create({
          set: setName.trim(),
          code: code.trim() || undefined,
          ...common
        })
    setBusy(false)
    if (!res.ok) return setError(res.error)
    for (const w of res.warnings ?? []) toast.warning(w)
    const data = res.data as { version?: number; new_version_created?: boolean }
    toast.success(
      data.new_version_created
        ? t('dialog.newVersion', { v: data.version ?? 0 })
        : t('dialog.saved')
    )
    onSaved(setName.trim())
    onClose()
  }

  return (
    <Dialog open onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{q ? t('dialog.edit', { code: q.code }) : t('dialog.new')}</DialogTitle>
          <DialogDescription>{q ? t('dialog.versionHint') : t('dialog.setHint')}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="flex flex-col gap-3">
            {!q && (
              <div className="grid grid-cols-[minmax(0,1fr)_7rem] gap-2">
                <FieldRow label={t('dialog.set')}>
                  <Input value={setName} onChange={(e) => setSetName(e.target.value)} />
                </FieldRow>
                <FieldRow label={t('dialog.code')}>
                  <Input
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="Q1"
                    className="font-mono"
                  />
                </FieldRow>
              </div>
            )}
            <FieldRow label={t('dialog.text')}>
              <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} />
            </FieldRow>
            <FieldRow label={t('dialog.expected')} help={t('dialog.expectedHint')}>
              <Textarea value={expected} onChange={(e) => setExpected(e.target.value)} rows={3} />
            </FieldRow>
            <div className="grid grid-cols-2 gap-2">
              <FieldRow label={t('dialog.type')}>
                <Select value={type} onValueChange={setType}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TYPES.map((x) => (
                      <SelectItem key={x} value={x}>
                        {x}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldRow>
              <FieldRow label={t('dialog.split')}>
                <Select value={split} onValueChange={setSplit}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t('dialog.noSplit')}</SelectItem>
                    {SPLITS.map((x) => (
                      <SelectItem key={x} value={x}>
                        {x}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldRow>
            </div>
          </div>

          <div className="flex min-w-0 flex-col gap-3">
            <FieldRow label={t('dialog.corpus')}>
              <Select value={corpusValue} onValueChange={setCorpus}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {corpora.map((c) => (
                    <SelectItem key={c.id} value={c.name}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldRow>
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-xs font-medium">{t('dialog.gold')}</div>
                <p className="text-[11px] text-muted-foreground">{t('dialog.goldHint')}</p>
              </div>
              <Button
                variant="outline"
                size="xs"
                onClick={() =>
                  setGold((g) => [...g, { document_id: documents[0] ?? '', text: '' }])
                }
              >
                <Plus /> {t('dialog.goldAdd')}
              </Button>
            </div>
            <div className="flex flex-col gap-2">
              {gold.map((g, i) => (
                <div key={i} className="flex flex-col gap-1.5 rounded-md border p-2">
                  <div className="flex gap-1.5">
                    <Select
                      value={g.document_id}
                      onValueChange={(v) =>
                        setGold((xs) => xs.map((x, j) => (j === i ? { ...x, document_id: v } : x)))
                      }
                    >
                      <SelectTrigger size="sm" className="min-w-0 flex-1 font-mono text-xs">
                        <SelectValue placeholder={t('dialog.goldDoc')} />
                      </SelectTrigger>
                      <SelectContent>
                        {[...new Set([...documents, g.document_id].filter(Boolean))].map((d) => (
                          <SelectItem key={d} value={d}>
                            {d}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={gt('common.delete')}
                      onClick={() => setGold((xs) => xs.filter((_, j) => j !== i))}
                    >
                      <X />
                    </Button>
                  </div>
                  <Textarea
                    value={g.text}
                    rows={2}
                    placeholder={t('dialog.goldText')}
                    onChange={(e) =>
                      setGold((xs) =>
                        xs.map((x, j) => (j === i ? { ...x, text: e.target.value } : x))
                      )
                    }
                    className="text-xs"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
        <ErrorAlert title={gt('common.error')} message={error} />
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            {gt('common.cancel')}
          </Button>
          <Button
            onClick={() => void submit()}
            disabled={busy || !text.trim() || (!q && !setName.trim())}
          >
            {busy && <LoaderCircle className="animate-spin" />}
            {gt('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
