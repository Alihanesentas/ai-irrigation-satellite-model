import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Farmer-facing palette: green for "healthy / approve", amber for
        // low-confidence prompts (docs/architecture.md#4, #9).
        brand: {
          50: "#f0f9f0",
          100: "#dcf0dc",
          500: "#3f8f3f",
          600: "#347434",
          700: "#295a29",
        },
        warn: {
          50: "#fffbeb",
          100: "#fef3c7",
          500: "#d97706",
          700: "#92400e",
        },
      },
    },
  },
  plugins: [],
};
export default config;
