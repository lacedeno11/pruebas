/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // OT Status colors
        'ot-preplanificada': '#3B82F6', // Blue
        'ot-planificada': '#FBBF24', // Yellow/Amber
        'ot-asignado': '#10B981', // Green
        'ot-detenida': '#F97316', // Orange
        'ot-anulada': '#EF4444', // Red
        'ot-finalizada': '#6B7280', // Gray

        // Project Type colors
        'project-publico': '#DC2626', // Red
        'project-privado': '#2563EB', // Blue
        'project-tercerizado': '#7C3AED', // Purple

        // Cuadrilla Type colors
        'cuadrilla-principal': '#059669', // Teal
        'cuadrilla-reserva': '#0891B2', // Cyan
      },
      backgroundColor: {
        'ot-preplanificada': '#DBEAFE', // Light blue
        'ot-planificada': '#FEF3C7', // Light yellow
        'ot-asignado': '#D1FAE5', // Light green
        'ot-detenida': '#FFEDD5', // Light orange
        'ot-anulada': '#FEE2E2', // Light red
        'ot-finalizada': '#F3F4F6', // Light gray
      },
      borderColor: {
        'ot-preplanificada': '#3B82F6',
        'ot-planificada': '#FBBF24',
        'ot-asignado': '#10B981',
        'ot-detenida': '#F97316',
        'ot-anulada': '#EF4444',
        'ot-finalizada': '#6B7280',
      },
      textColor: {
        'ot-preplanificada': '#1E40AF', // Dark blue
        'ot-planificada': '#92400E', // Dark yellow
        'ot-asignado': '#065F46', // Dark green
        'ot-detenida': '#7C2D12', // Dark orange
        'ot-anulada': '#7F1D1D', // Dark red
        'ot-finalizada': '#374151', // Dark gray
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.3s ease-in',
        slideInRight: 'slideInRight 0.3s ease-out',
        slideInLeft: 'slideInLeft 0.3s ease-out',
        pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      spacing: {
        'safe-bottom': 'env(safe-area-inset-bottom)',
        'safe-top': 'env(safe-area-inset-top)',
        'safe-left': 'env(safe-area-inset-left)',
        'safe-right': 'env(safe-area-inset-right)',
      },
    },
  },
  plugins: [],
};

