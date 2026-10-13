import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/shared/empty-state'
import { useT } from '@/hooks/use-t'
import { DEFAULT_ROUTE } from '@/lib/routes'

export default function NotFoundPage(): React.JSX.Element {
  const t = useT()
  return (
    <EmptyState
      title={t('page.notFound.title')}
      description={t('page.notFound.description')}
      action={
        <Button asChild size="sm">
          <Link to={`/${DEFAULT_ROUTE}`}>{t('page.notFound.back')}</Link>
        </Button>
      }
    />
  )
}
