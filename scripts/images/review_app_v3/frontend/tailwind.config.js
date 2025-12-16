/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Status colors
        'status-clean': '#22c55e',
        'status-warning': '#f59e0b',
        'status-danger': '#ef4444',
        // Detection type colors
        'type-duplicate': '#3b82f6',
        'type-similar': '#8b5cf6',
        'type-outlier': '#f97316',
      },
    },
  },
  plugins: [],
}
