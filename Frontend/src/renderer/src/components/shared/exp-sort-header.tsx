import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { TableHead } from '@/components/ui/table'
import { cn } from '@/lib/utils'

import type { SortState } from './exp-sort'

export type { SortState }

/** Clickable table header cell toggling sort. */
export function SortHeader({
  colKey,
  sort,
  onSort,
  children,
  className,
  numeric = false
}: {
  colKey: string
  sort: SortState | null
  onSort: (next: SortState) => void
  children: React.ReactNode
  className?: string
  numeric?: boolean
}): React.JSX.Element {
  const active = sort?.key === colKey
  const Icon = !active ? ArrowUpDown : sort.dir === 'asc' ? ArrowUp : ArrowDown
  return (
    <TableHead className={cn('whitespace-nowrap', numeric && 'text-right', className)}>
      <button
        type="button"
        className={cn(
          'inline-flex items-center gap-1 hover:text-foreground',
          active ? 'text-foreground' : 'text-muted-foreground'
        )}
        onClick={() => onSort({ key: colKey, dir: active && sort.dir === 'desc' ? 'asc' : 'desc' })}
      >
        {children}
        <Icon className="size-3" />
      </button>
    </TableHead>
  )
}
