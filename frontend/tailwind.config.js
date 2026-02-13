/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'publico-blue': '#3B82F6',
        'privado-green': '#10B981',
        'tercerizado-orange': '#F97316',
        'status-preplanificada': '#9CA3AF',
        'status-planificada': '#3B82F6',
        'status-asignado': '#FBBF24',
        'status-detenida': '#F97316',
        'status-anulada': '#EF4444',
        'status-finalizada': '#10B981',
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}

