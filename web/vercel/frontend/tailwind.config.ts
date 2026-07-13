import type { Config } from 'tailwindcss';

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'hsl(var(--bg))',
        surface: 'hsl(var(--surface))',
        'surface-alt': 'hsl(var(--surface-alt))',
        border: 'hsl(var(--border))',
        text: 'hsl(var(--text))',
        'text-muted': 'hsl(var(--text-muted))',
        'text-faint': 'hsl(var(--text-faint))',
        primary: 'hsl(var(--primary))',
        'primary-hover': 'hsl(var(--primary-hover))',
        secondary: 'hsl(var(--secondary))',
        'secondary-hover': 'hsl(var(--secondary-hover))',
        error: 'hsl(var(--error))',
        warning: 'hsl(var(--warning))',
        success: 'hsl(var(--success))',
      },
      fontFamily: {
        sans: ['General Sans', 'Satoshi', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.9375rem', { lineHeight: '1.5rem' }],
        lg: ['1.0625rem', { lineHeight: '1.6rem' }],
        xl: ['1.375rem', { lineHeight: '1.8rem' }],
      },
      borderRadius: {
        DEFAULT: '6px',
        lg: '8px',
      },
    },
  },
  plugins: [],
} satisfies Config;
