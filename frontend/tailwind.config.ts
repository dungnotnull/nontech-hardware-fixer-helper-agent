import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: { 50: "#f0fdf4", 500: "#22c55e", 600: "#16a34a", 700: "#15803d" },
        danger: { 50: "#fef2f2", 500: "#ef4444", 600: "#dc2626" },
        warning: { 50: "#fffbeb", 500: "#f59e0b", 600: "#d97706" },
      },
    },
  },
  plugins: [],
};
export default config;