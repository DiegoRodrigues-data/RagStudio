import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export interface ComboSuggestion {
  value: string
  hint?: string
}

interface ComboInputProps {
  id?: string
  value: string
  onChange: (value: string) => void
  suggestions: ComboSuggestion[]
  placeholder?: string
  suggestionsLabel?: string
  emptyLabel?: string
  disabled?: boolean
  className?: string
}

/** Free-text input with a dropdown of suggestions (model names, etc.). */
export function ComboInput({
  id,
  value,
  onChange,
  suggestions,
  placeholder,
  suggestionsLabel,
  emptyLabel,
  disabled,
  className
}: ComboInputProps): React.JSX.Element {
  return (
    <div className={cn('flex gap-1', className)}>
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="font-mono text-xs"
      />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="icon"
            disabled={disabled}
            aria-label={suggestionsLabel}
          >
            <ChevronDown className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="max-h-72 overflow-auto">
          {suggestionsLabel && <DropdownMenuLabel>{suggestionsLabel}</DropdownMenuLabel>}
          {suggestionsLabel && <DropdownMenuSeparator />}
          {suggestions.length === 0 && (
            <DropdownMenuItem disabled>{emptyLabel ?? '—'}</DropdownMenuItem>
          )}
          {suggestions.map((s) => (
            <DropdownMenuItem key={s.value} onSelect={() => onChange(s.value)}>
              <span className="flex-1 font-mono text-xs">{s.value}</span>
              {s.hint && <span className="text-xs text-muted-foreground">{s.hint}</span>}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
