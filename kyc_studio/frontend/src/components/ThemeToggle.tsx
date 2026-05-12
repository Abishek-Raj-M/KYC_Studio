import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="surface-glass inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-panel text-fg shadow-card transition hover:scale-[1.03]"
      aria-label="Toggle color theme"
      title="Toggle color theme"
    >
      {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  )
}
