import { Checkbox } from '@/components/ui/checkbox'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { LoadingState } from './loading-state'

export interface DataTableColumn<T> {
  id: string
  header: React.ReactNode
  cell: (row: T) => React.ReactNode
  className?: string
  headerClassName?: string
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string
  loading?: boolean
  /** Rendered instead of the table body when `rows` is empty (and not loading). */
  empty?: React.ReactNode
  selectable?: boolean
  selected?: Set<string>
  onSelectedChange?: (next: Set<string>) => void
  onRowClick?: (row: T) => void
  selectAllLabel?: string
  selectRowLabel?: string
  className?: string
}

/** Lightweight data table (no external table library): columns, optional selection, row click. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  empty,
  selectable = false,
  selected,
  onSelectedChange,
  onRowClick,
  selectAllLabel = 'Select all',
  selectRowLabel = 'Select row',
  className
}: DataTableProps<T>): React.JSX.Element {
  if (loading) return <LoadingState rows={5} className={className} />
  if (rows.length === 0 && empty) return <>{empty}</>

  const sel = selected ?? new Set<string>()
  const allSelected = rows.length > 0 && rows.every((r) => sel.has(rowKey(r)))
  const someSelected = !allSelected && rows.some((r) => sel.has(rowKey(r)))

  const toggleAll = (checked: boolean): void => {
    const next = new Set(sel)
    for (const r of rows) {
      if (checked) next.add(rowKey(r))
      else next.delete(rowKey(r))
    }
    onSelectedChange?.(next)
  }

  const toggleOne = (key: string, checked: boolean): void => {
    const next = new Set(sel)
    if (checked) next.add(key)
    else next.delete(key)
    onSelectedChange?.(next)
  }

  return (
    <div className={cn('overflow-auto rounded-md border', className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {selectable && (
              <TableHead className="w-10">
                <Checkbox
                  aria-label={selectAllLabel}
                  checked={allSelected ? true : someSelected ? 'indeterminate' : false}
                  onCheckedChange={(c) => toggleAll(c === true)}
                />
              </TableHead>
            )}
            {columns.map((c) => (
              <TableHead key={c.id} className={c.headerClassName}>
                {c.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => {
            const key = rowKey(row)
            return (
              <TableRow
                key={key}
                data-state={sel.has(key) ? 'selected' : undefined}
                className={cn(onRowClick && 'cursor-pointer')}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {selectable && (
                  <TableCell className="w-10" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      aria-label={selectRowLabel}
                      checked={sel.has(key)}
                      onCheckedChange={(c) => toggleOne(key, c === true)}
                    />
                  </TableCell>
                )}
                {columns.map((c) => (
                  <TableCell key={c.id} className={c.className}>
                    {c.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
