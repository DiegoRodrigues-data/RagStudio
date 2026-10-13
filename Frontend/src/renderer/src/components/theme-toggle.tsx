import { Check, Monitor, Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { useTheme } from '@/hooks/use-theme'
import { useT } from '@/hooks/use-t'
import type { Theme } from '@/lib/theme'

const OPTIONS: {
  value: Theme
  icon: typeof Sun
  labelKey: 'theme.light' | 'theme.dark' | 'theme.system'
}[] = [
  { value: 'light', icon: Sun, labelKey: 'theme.light' },
  { value: 'dark', icon: Moon, labelKey: 'theme.dark' },
  { value: 'system', icon: Monitor, labelKey: 'theme.system' }
]

export function ThemeToggle(): React.JSX.Element {
  const t = useT()
  const { theme, resolvedTheme, setTheme } = useTheme()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={t('theme.toggle')}
          title={t('theme.toggle')}
        >
          {resolvedTheme === 'dark' ? <Moon className="size-4" /> : <Sun className="size-4" />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {OPTIONS.map((opt) => (
          <DropdownMenuItem key={opt.value} onSelect={() => setTheme(opt.value)}>
            <opt.icon className="size-4" />
            <span className="flex-1">{t(opt.labelKey)}</span>
            {theme === opt.value && <Check className="size-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
