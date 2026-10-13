import { CircleX } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

interface ErrorAlertProps {
  title: string
  message?: string | null
  retryLabel?: string
  onRetry?: () => void
  className?: string
}

/** Destructive alert for a failed backend call, with optional retry. */
export function ErrorAlert({
  title,
  message,
  retryLabel,
  onRetry,
  className
}: ErrorAlertProps): React.JSX.Element | null {
  if (!message) return null
  return (
    <Alert variant="destructive" className={className}>
      <CircleX className="size-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <pre className="max-h-40 w-full overflow-auto font-mono text-xs whitespace-pre-wrap break-all">
          {message}
        </pre>
        {onRetry && retryLabel && (
          <Button variant="outline" size="sm" className="mt-2 w-fit" onClick={onRetry}>
            {retryLabel}
          </Button>
        )}
      </AlertDescription>
    </Alert>
  )
}
