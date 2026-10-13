import { useTechniqueTitle } from '@/hooks/use-technique-title'

/** Display name of a technique; the identifier stored with the runs is the tooltip. */
export function TechniqueName({
  name,
  className
}: {
  name: string
  className?: string
}): React.JSX.Element {
  const title = useTechniqueTitle()
  return (
    <span className={className} title={name}>
      {title(name)}
    </span>
  )
}
