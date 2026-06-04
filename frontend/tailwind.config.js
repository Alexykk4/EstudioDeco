/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Roboto', 'sans-serif'],
      },
      colors: {
        brand: {
          light: '#f3f0ff',
          DEFAULT: '#9b8cfb',
          dark: '#7c6ce0',
        },
        success: {
          light: '#d1fae5',
          DEFAULT: '#10b981',
        },
        danger: {
          light: '#fee2e2',
          DEFAULT: '#ef4444',
        },
        surface: {
          50: '#f8f9fa',
          100: '#ffffff',
          200: '#f1f5f9',
        },
        text: {
          main: '#334155',
          muted: '#64748b',
        }
      },
      boxShadow: {
        'volt': '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
        'volt-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)',
      }
    },
  },
  plugins: [],
}
