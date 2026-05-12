/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        body: ['"Plus Jakarta Sans"', 'sans-serif'],
        heading: ['"Outfit"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        page: 'var(--color-page)',
        raised: 'var(--color-raised)',
        panel: 'var(--color-panel)',
        'panel-muted': 'var(--color-panel-muted)',
        border: 'var(--color-border)',
        fg: 'var(--color-fg)',
        'fg-muted': 'var(--color-fg-muted)',
        link: 'var(--link-color)',
        focus: 'var(--focus-ring-outer)',
        brand: 'var(--brand-solid)',
      },
      boxShadow: {
        panel: 'var(--shadow-panel)',
        card: 'var(--shadow-card)',
      },
    },
  },
  plugins: [],
}
