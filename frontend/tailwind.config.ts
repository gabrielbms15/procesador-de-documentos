import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        concreto: {
          DEFAULT: "#464B4F",
          dark: "#2F3438",
          light: "#697076",
          ultralight: "#E4E7E9",
        },
        terracota: {
          DEFAULT: "#9E473E",
          dark: "#7F3830",
          light: "#B85C52",
          tint: "#F9ECEB",
        },
        arena: {
          DEFAULT: "#C6A774",
          light: "#F7F4EE",
          dark: "#A38553",
        },
        naranja: {
          DEFAULT: "#D9531E",
          hover: "#C24615",
          tint: "#FDF0EB",
        },
        industrial: {
          50: "#F8F9FA",
          100: "#F1F3F4",
          200: "#E5E8EB",
          300: "#D3D7DC",
          400: "#9AA1A9",
          500: "#5D646B",
          800: "#24282B",
          900: "#181A1C",
        },
      },
      fontFamily: {
        condensed: ["var(--font-barlow-condensed)", "sans-serif"],
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
