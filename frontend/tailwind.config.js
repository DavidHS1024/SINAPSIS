/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta institucional SINAPSIS
        marino: {
          900: "#0A1F3C",  // fondo profundo
          800: "#0F2847",  // fondo base
          700: "#173456",  // superficies elevadas
          600: "#1F4470",  // bordes / acentos suaves
        },
        acento: {
          DEFAULT: "#C6A45C",  // dorado institucional
          claro: "#E4D3A8",
        },
        niebla: "#E8EEF5",     // texto claro
      },
      fontFamily: {
        display: ["Georgia", "Cambria", "serif"],
        sans: ["Segoe UI", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
