/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0f",
        surface: "#111118",
        surface2: "#16161f",
        border: "#1e1e2e",
        accent: {
          green: "#00ff88",
          orange: "#ff6b00",
          red: "#ff2244",
          yellow: "#ffcc00",
        },
        txt: {
          primary: "#e0e0e0",
          dim: "#555570",
          mid: "#8a8aa0",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(0, 255, 136, 0.25)",
        "glow-orange": "0 0 24px rgba(255, 107, 0, 0.35)",
        "glow-red": "0 0 24px rgba(255, 34, 68, 0.4)",
      },
      keyframes: {
        scanline: {
          "0%": { transform: "translateY(0%)" },
          "100%": { transform: "translateY(100%)" },
        },
        "pulse-border": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(0,255,136,0.5)" },
          "50%": { boxShadow: "0 0 24px 4px rgba(0,255,136,0.4)" },
        },
        blink: {
          "0%, 50%": { opacity: 1 },
          "50.01%, 100%": { opacity: 0 },
        },
      },
      animation: {
        scanline: "scanline 4s linear infinite",
        "pulse-border": "pulse-border 1.6s ease-in-out infinite",
        blink: "blink 1s steps(1) infinite",
      },
    },
  },
  plugins: [],
};
