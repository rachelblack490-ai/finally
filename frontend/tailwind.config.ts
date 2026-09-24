import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // FinAlly palette (planning/CURSOR_PLAN.md §1)
        bg: {
          DEFAULT: "#0d1117",
          panel: "#1a1a2e",
        },
        finally: {
          yellow: "#ecad0a",
          blue: "#209dd7",
          purple: "#753991",
        },
        up: "#16c784",
        down: "#ea3943",
      },
      keyframes: {
        flashUp: {
          "0%": { backgroundColor: "rgba(22,199,132,0.45)" },
          "100%": { backgroundColor: "transparent" },
        },
        flashDown: {
          "0%": { backgroundColor: "rgba(234,57,67,0.45)" },
          "100%": { backgroundColor: "transparent" },
        },
      },
      animation: {
        flashUp: "flashUp 0.5s ease-out",
        flashDown: "flashDown 0.5s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
