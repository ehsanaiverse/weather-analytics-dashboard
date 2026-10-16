/** Tailwind CSS configuration.
 *
 * Colours are exposed as CSS variables (see `src/index.css`) and referenced
 * here with the alpha channel intact, so a utility such as `bg-surface/80`
 * keeps working in both themes.
 *
 * The data-visualisation tokens mirror `app/config.py` in the Python project so
 * the React charts and the Streamlit dashboard share one palette.
 */

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        panel: 'rgb(var(--color-panel) / <alpha-value>)',
        elevated: 'rgb(var(--color-elevated) / <alpha-value>)',
        ink: 'rgb(var(--color-ink) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        line: 'rgb(var(--color-line) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        'accent-soft': 'rgb(var(--color-accent-soft) / <alpha-value>)',
        temperature: 'rgb(var(--color-temperature) / <alpha-value>)',
        humidity: 'rgb(var(--color-humidity) / <alpha-value>)',
        precipitation: 'rgb(var(--color-precipitation) / <alpha-value>)',
        'temperature-min': 'rgb(var(--color-temperature-min) / <alpha-value>)',
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
      },
      maxWidth: {
        content: '90rem',
      },
    },
  },
  plugins: [],
}