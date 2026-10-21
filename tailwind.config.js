/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html"
  ],
  safelist: [
    "bg-sky-50",
    "text-sky-700",
    "bg-amber-50",
    "text-amber-700",
    "bg-emerald-50",
    "text-emerald-700"
  ],
  theme: {
    extend: {}
  },
  plugins: []
};
