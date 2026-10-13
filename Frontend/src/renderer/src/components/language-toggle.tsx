import { Check, Languages } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { useLanguage } from '@/hooks/use-t'
import { LANGUAGES, type Language, type TranslationKey } from '@/lib/i18n'

const SHORT: Record<Language, string> = { 'pt-BR': 'PT', en: 'EN' }

export function LanguageToggle(): React.JSX.Element {
  const { language, setLanguage, t } = useLanguage()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          aria-label={t('language.toggle')}
          title={t('language.toggle')}
          className="gap-1.5"
        >
          <Languages className="size-4" />
          <span className="text-xs font-medium">{SHORT[language]}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {LANGUAGES.map((lang) => (
          <DropdownMenuItem key={lang} onSelect={() => setLanguage(lang)}>
            <span className="flex-1">{t(`language.${lang}` as TranslationKey)}</span>
            {language === lang && <Check className="size-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
