'use client'

import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  useEffect(() => {
    const saved = window.localStorage.getItem('medicheck-theme') as 'light' | 'dark' | null
    const next = saved ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    document.documentElement.classList.toggle('dark', next === 'dark')
    document.documentElement.classList.toggle('light', next === 'light')
    setTheme(next)
  }, [])

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.classList.toggle('dark', next === 'dark')
    document.documentElement.classList.toggle('light', next === 'light')
    window.localStorage.setItem('medicheck-theme', next)
    setTheme(next)
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
      title={theme === 'dark' ? 'Giao diện sáng' : 'Giao diện tối'}
      className="flex size-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-sky-500 dark:hover:bg-slate-700"
    >
      {theme === 'dark' ? <Sun className="size-[17px]" /> : <Moon className="size-[17px]" />}
    </button>
  )
}
