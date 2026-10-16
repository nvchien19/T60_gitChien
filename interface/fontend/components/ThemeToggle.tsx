'use client'

import { useEffect, useId, useState } from 'react'

import styles from './ThemeToggle.module.css'

type Theme = 'light' | 'dark'

type ThemeToggleProps = {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  compact?: boolean
}

const STORAGE_KEY = 'medicheck-theme'

function applyTheme(theme: Theme) {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  root.classList.toggle('light', theme === 'light')
  root.style.colorScheme = theme
}

export function ThemeToggle({ checked, onCheckedChange, compact = false }: ThemeToggleProps = {}) {
  const [theme, setTheme] = useState<Theme>('light')
  const id = useId().replaceAll(':', '')
  const isControlled = checked !== undefined
  const isDark = isControlled ? checked : theme === 'dark'

  useEffect(() => {
    if (isControlled) return
    let saved: string | null = null
    try {
      saved = window.localStorage.getItem(STORAGE_KEY)
    } catch {
      // The switch still works when storage is unavailable.
    }
    const next: Theme = saved === 'dark' ? 'dark' : 'light'
    applyTheme(next)
    setTheme(next)
  }, [isControlled])

  const toggleTheme = () => {
    if (isControlled) {
      onCheckedChange?.(!checked)
      return
    }
    const next: Theme = document.documentElement.classList.contains('dark') ? 'light' : 'dark'
    applyTheme(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Keep the selected theme for this page even without storage.
    }
    setTheme(next)
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label="Giao diện tối"
      title={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
      data-mode={isDark ? 'dark' : 'light'}
      data-compact={compact ? 'true' : undefined}
      className={`${styles.toggle} theme-toggle`}
      onClick={toggleTheme}
    >
      <svg className={styles.art} viewBox="0 0 320 132" aria-hidden="true" focusable="false">
        <defs>
          <clipPath id={`${id}-track`}>
            <rect x="4" y="4" width="312" height="124" rx="62" />
          </clipPath>
          <linearGradient id={`${id}-day`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#1479bc" />
            <stop offset="0.6" stopColor="#73b8e7" />
            <stop offset="1" stopColor="#d9effb" />
          </linearGradient>
          <linearGradient id={`${id}-night`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#171e30" />
            <stop offset="0.6" stopColor="#363c4d" />
            <stop offset="1" stopColor="#757783" />
          </linearGradient>
          <linearGradient id={`${id}-sun`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ffe545" />
            <stop offset="1" stopColor="#ffbf23" />
          </linearGradient>
          <linearGradient id={`${id}-moon`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#f3f5f8" />
            <stop offset="1" stopColor="#bdc8d8" />
          </linearGradient>
        </defs>

        <g clipPath={`url(#${id}-track)`}>
          <g className={styles.dayScene}>
            <rect width="320" height="132" fill={`url(#${id}-day)`} />
            <circle cx="66" cy="66" r="86" fill="#fff" opacity=".22" />
            <circle cx="66" cy="66" r="119" fill="#fff" opacity=".15" />
            <circle cx="66" cy="66" r="151" fill="#fff" opacity=".1" />
            <g fill="#b9ddf4">
              <circle cx="182" cy="116" r="37" />
              <circle cx="216" cy="111" r="43" />
              <circle cx="258" cy="82" r="40" />
              <circle cx="301" cy="75" r="50" />
            </g>
            <g fill="#d9effc">
              <circle cx="156" cy="126" r="26" />
              <circle cx="191" cy="131" r="30" />
              <circle cx="226" cy="119" r="29" />
              <circle cx="263" cy="114" r="39" />
              <circle cx="307" cy="119" r="43" />
            </g>
          </g>

          <g className={styles.nightScene}>
            <rect width="320" height="132" fill={`url(#${id}-night)`} />
            <circle cx="258" cy="66" r="84" fill="#fff" opacity=".18" />
            <circle cx="258" cy="66" r="119" fill="#fff" opacity=".12" />
            <circle cx="258" cy="66" r="151" fill="#fff" opacity=".08" />
            <g fill="#bac4d3">
              <circle cx="24" cy="65" r="1.6" />
              <circle cx="86" cy="65" r="1.8" />
              <circle cx="118" cy="28" r="1.7" />
              <circle cx="113" cy="103" r="2.4" />
              <circle cx="144" cy="49" r="2.5" />
              <circle cx="183" cy="64" r="1.8" />
            </g>
            <g fill="#d5dbe5">
              <path d="M65 20l2.1 4.6L72 27l-4.9 2.3L65 34l-2.1-4.7L58 27l4.9-2.4z" />
              <path d="M169 19l2 4.3 4.4 2.1-4.4 2.1-2 4.4-2-4.4-4.5-2.1 4.5-2.1z" />
              <path d="M148 91l2 4.5 4.6 2.1-4.6 2.1-2 4.6-2-4.6-4.6-2.1 4.6-2.1z" />
            </g>
          </g>

          <g className={styles.knob}>
            <circle className={styles.sun} cx="65" cy="66" r="52" fill={`url(#${id}-sun)`} stroke="#fff1a3" strokeWidth="2.5" />
            <circle className={styles.moon} cx="65" cy="66" r="52" fill={`url(#${id}-moon)`} stroke="#edf1f6" strokeWidth="2.5" />
            <g className={styles.craters} fill="#9fb2c7" stroke="#829aaf" strokeWidth="1.5">
              <circle cx="42" cy="68" r="16" />
              <circle cx="66" cy="39" r="8" />
              <circle cx="88" cy="91" r="11" />
            </g>
          </g>
        </g>
        <rect x="2" y="2" width="316" height="128" rx="64" fill="none" stroke="#aabbd0" strokeWidth="3" />
        <rect x="5" y="5" width="310" height="122" rx="61" fill="none" stroke="#ffffff" strokeOpacity=".5" strokeWidth="2" />
      </svg>
    </button>
  )
}
