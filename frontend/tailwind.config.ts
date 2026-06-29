import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#6366f1",   // Indigo primary
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },
        surface: {
          DEFAULT: "#F6F8FC",
          card:    "#FFFFFF",
          input:   "#F6F8FC",
          border:  "#E2E8F0",
        },
        success: {
          DEFAULT: "#10B981", // Emerald
          50:  "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          500: "#10b981",
          600: "#059669",
        },
        secondary: {
          DEFAULT: "#3B82F6", // Blue
          50:  "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
        },
        accent: {
          DEFAULT: "#8B5CF6", // Lavender
          50:  "#f5f3ff",
          100: "#ede9fe",
          500: "#8b5cf6",
        }
      },
      boxShadow: {
        "neo-raised": "6px 6px 12px #d5deeb, -6px -6px 12px #ffffff",
        "neo-raised-lg": "10px 10px 25px #d5deeb, -10px -10px 25px #ffffff",
        "neo-raised-sm": "3px 3px 6px #d5deeb, -3px -3px 6px #ffffff",
        "neo-inset": "inset 4px 4px 8px #d1d9e6, inset -4px -4px 8px #ffffff",
        "neo-inset-white": "inset 4px 4px 8px #e2e8f0, inset -4px -4px 8px #ffffff",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "Consolas", "monospace"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "brand-gradient": "linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)",
      },
      animation: {
        "fade-in":     "fadeIn 0.4s ease-out",
        "slide-up":    "slideUp 0.5s ease-out",
        "pulse-slow":  "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "shimmer":     "shimmer 2s infinite",
      },
      keyframes: {
        fadeIn:  { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp: { from: { opacity: "0", transform: "translateY(20px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        shimmer: { from: { backgroundPosition: "-200% 0" }, to: { backgroundPosition: "200% 0" } },
      },
    },
  },
  plugins: [],
};

export default config;
