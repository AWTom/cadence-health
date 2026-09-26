/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Colorblind-safe tier palette (blue→orange, not red/green)
        tier1: { bg: "#dbeafe", text: "#1e40af", border: "#93c5fd" },
        tier2: { bg: "#e0f2fe", text: "#0369a1", border: "#7dd3fc" },
        tier3: { bg: "#fef9c3", text: "#854d0e", border: "#fde047" },
        tier4: { bg: "#fed7aa", text: "#9a3412", border: "#fb923c" },
        tier5: { bg: "#ff6b2b", text: "#fff", border: "#c2410c" },
      },
    },
  },
  plugins: [],
};
