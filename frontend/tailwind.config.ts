import type { Config } from "tailwindcss";

const config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        nexus: {
          bg: "rgb(var(--nexus-bg) / <alpha-value>)",
          panel: "rgb(var(--nexus-panel) / <alpha-value>)",
          card: "rgb(var(--nexus-card) / <alpha-value>)",
          fg: "rgb(var(--nexus-fg) / <alpha-value>)",
          muted: "rgb(var(--nexus-muted) / <alpha-value>)",
          accent: "rgb(var(--nexus-accent) / <alpha-value>)",
          secondary: "rgb(var(--nexus-secondary) / <alpha-value>)",
          border: "rgb(var(--nexus-border) / <alpha-value>)",
        },
        ai: {
          blue: "#2563EB",
          "blue-light": "#60A5FA",
          "blue-dark": "#1D4ED8",
          cyan: "#38BDF8",
          "cyan-light": "#7DD3FC",
          purple: "#7C3AED",
          "purple-light": "#A78BFA",
          indigo: "#4F46E5",
          violet: "#8B5CF6",
          emerald: "#10B981",
          rose: "#F43F5E",
          amber: "#F59E0B",
          glow: "rgba(37, 99, 235, 0.35)",
        }
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        "2xl": "1.25rem",
        "3xl": "1.75rem",
        "4xl": "2.25rem",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "var(--font-inter)", "system-ui", "sans-serif"],
        heading: ["'Instrument Serif'", "var(--font-space-grotesk)", "system-ui", "sans-serif"],
        body: ["'Barlow'", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.04em",
        tighter: "-0.025em",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.8", transform: "scale(1.05)", boxShadow: "0 0 20px rgba(10, 132, 255, 0.6)" },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        "gradient-shift": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "border-pulse": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        "spin-slow": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        "mesh-drift": {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "33%": { transform: "translate(30px, -20px) scale(1.05)" },
          "66%": { transform: "translate(-20px, 20px) scale(0.95)" },
        },
        "wave-bar": {
          "0%, 100%": { transform: "scaleY(0.4)" },
          "50%": { transform: "scaleY(1)" },
        },
        "aurora": {
          "0%, 100%": { transform: "translate3d(0, 0, 0) rotate(0deg)" },
          "33%": { transform: "translate3d(40px, -30px, 0) rotate(2deg)" },
          "66%": { transform: "translate3d(-30px, 30px, 0) rotate(-2deg)" },
        },
        "counter": {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "pulse-glow": "pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float": "float 3s ease-in-out infinite",
        "gradient-shift": "gradient-shift 8s ease infinite",
        "shimmer": "shimmer 2.5s linear infinite",
        "fade-up": "fade-up 0.7s cubic-bezier(0.16, 1, 0.3, 1) both",
        "scale-in": "scale-in 0.5s cubic-bezier(0.16, 1, 0.3, 1) both",
        "border-pulse": "border-pulse 2.4s ease-in-out infinite",
        "spin-slow": "spin-slow 14s linear infinite",
        "spin-slower": "spin-slow 30s linear infinite",
        "mesh-drift": "mesh-drift 16s ease-in-out infinite",
        "wave-bar": "wave-bar 1.1s ease-in-out infinite",
        "aurora": "aurora 20s ease-in-out infinite",
      },
      boxShadow: {
        "glow-blue": "0 0 30px -5px rgba(10, 132, 255, 0.45), 0 8px 24px -8px rgba(10, 132, 255, 0.35)",
        "glow-purple": "0 0 30px -5px rgba(191, 90, 242, 0.45), 0 8px 24px -8px rgba(191, 90, 242, 0.35)",
        "glow-cyan": "0 0 30px -5px rgba(50, 215, 75, 0.4), 0 8px 24px -8px rgba(50, 215, 75, 0.3)",
        "glow-emerald": "0 0 30px -5px rgba(16, 185, 129, 0.45), 0 8px 24px -8px rgba(16, 185, 129, 0.35)",
        "inner-highlight": "inset 0 1px 0 0 rgba(255,255,255,0.08), inset 0 0 0 1px rgba(255,255,255,0.04)",
        "inner-highlight-strong": "inset 0 1px 0 0 rgba(255,255,255,0.14), inset 0 0 0 1px rgba(255,255,255,0.06)",
        "soft": "0 1px 2px 0 rgba(0,0,0,0.04), 0 4px 16px -4px rgba(0,0,0,0.08)",
        "elevated": "0 1px 2px 0 rgba(0,0,0,0.04), 0 12px 32px -8px rgba(0,0,0,0.12), 0 24px 48px -12px rgba(0,0,0,0.08)",
      },
      backgroundImage: {
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, #0A84FF 0deg, #BF5AF2 180deg, #0A84FF 360deg)",
        "mesh-hero": "radial-gradient(at 27% 37%, hsla(215, 98%, 61%, 0.35) 0px, transparent 50%), radial-gradient(at 97% 21%, hsla(280, 98%, 61%, 0.28) 0px, transparent 50%), radial-gradient(at 52% 99%, hsla(154, 98%, 50%, 0.18) 0px, transparent 50%), radial-gradient(at 10% 29%, hsla(256, 96%, 67%, 0.25) 0px, transparent 50%), radial-gradient(at 97% 96%, hsla(38, 60%, 74%, 0.15) 0px, transparent 50%)",
        "noise": "url(\"data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.18 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")",
        "dot-grid": "radial-gradient(circle, rgba(148, 163, 184, 0.18) 1px, transparent 1px)",
        "line-grid": "linear-gradient(to right, rgba(148, 163, 184, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(148, 163, 184, 0.08) 1px, transparent 1px)",
        "shimmer-bar": "linear-gradient(110deg, transparent 35%, rgba(255,255,255,0.45) 50%, transparent 65%)",
      },
      backgroundSize: {
        "dot-grid": "24px 24px",
        "line-grid": "44px 44px",
        "200": "200% 100%",
      },
      transitionTimingFunction: {
        "expo-out": "cubic-bezier(0.16, 1, 0.3, 1)",
        "expo-in": "cubic-bezier(0.7, 0, 0.84, 0)",
        "soft-spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;

export default config;
