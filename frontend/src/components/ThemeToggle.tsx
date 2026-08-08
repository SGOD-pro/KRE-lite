import React, { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

// ── Theme persistence key ─────────────────────────────────────────────────────
const THEME_KEY = 'kre-theme';

function applyTheme(dark: boolean) {
  if (dark) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

export const ThemeToggle: React.FC = () => {
  const [dark, setDark] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      if (stored !== null) return stored === 'dark';
    } catch {}
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
  });

  // Apply on mount + whenever dark changes
  useEffect(() => {
    applyTheme(dark);
    try { localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light'); } catch {}
  }, [dark]);

  const toggle = () => {
    const next = !dark;
    const switchTheme = () => setDark(next);

    // Use View Transition API for the circular ripple if available
    if (!(document as any).startViewTransition) {
      switchTheme();
    } else {
      (document as any).startViewTransition(switchTheme);
    }
  };

  return (
    <button
      id="theme-toggle"
      data-testid="theme-toggle"
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={toggle}
      style={{ position: 'fixed', top: 16, left: 16, zIndex: 9999 }}
      className="p-2 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur border border-[#e2e8f0] dark:border-[#1e293b] shadow-sm transition-colors hover:bg-[#f1f5f9] dark:hover:bg-[#1e293b] text-[#64748b] dark:text-[#94a3b8] cursor-pointer"
      title={dark ? 'Light mode' : 'Dark mode'}
    >
      {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  );
};
