/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['DM Mono', 'SF Mono', 'Menlo', 'monospace'],
      },
      colors: {
        // Databricks Brand Colors
        'db-lava': {
          600: '#FF3621',
          500: '#FF5240',
          400: '#FF7A6A',
        },
        'db-navy': {
          900: '#0B2026',
          800: '#132A32',
          700: '#1E3A44',
        },
        'db-oat': {
          medium: '#EEEDE9',
          light: '#F9F7F4',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
