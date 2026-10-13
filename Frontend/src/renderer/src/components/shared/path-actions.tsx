import { ExternalLink, FolderOpen } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useT } from '@/hooks/use-t'

/** Open a generated file with the OS default app, or reveal it in the file manager. */
export function PathActions({
  path,
  size = 'xs'
}: {
  path: string
  size?: 'xs' | 'sm'
}): React.JSX.Element {
  const t = useT()
  const open = async (): Promise<void> => {
    try {
      await window.api.openPath(path)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }
  return (
    <span className="inline-flex gap-1">
      <Button variant="outline" size={size} onClick={() => void open()}>
        <ExternalLink /> {t('common.open')}
      </Button>
      <Button variant="ghost" size={size} onClick={() => void window.api.showInFolder(path)}>
        <FolderOpen /> {t('common.showInFolder')}
      </Button>
    </span>
  )
}
