/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        field: {
          soccer: '#2d8a4e',
          basketball: '#c6884a',
          baseball: '#5a8f3c',
        },
      },
    },
  },
  plugins: [],
};
