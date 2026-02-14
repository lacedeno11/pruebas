/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // OT status colors
        preplanificada: "#bfdbfe", // blue-200
        planificada: "#fef08a",    // yellow-200
        asignado: "#bbf7d0",       // green-200
        detenida: "#fecaca",       // red-200
        anulada: "#d1d5db",        // gray-300
        finalizada: "#86efac",     // green-400
      },
    },
  },
  plugins: [],
}

