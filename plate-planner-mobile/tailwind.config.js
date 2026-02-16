/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: "#FF6B4A", // Coral Orange
        secondary: "#86C649", // Avocado Green
        surface: "#FAFAFA",
        dark: "#1F2937",
      },
    },
  },
  plugins: [],
};
