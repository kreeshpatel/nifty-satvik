/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      fontFamily: {
        // DM Sans EVERYWHERE (locked 2026-04-25 per user). Tabular numerals
        // are produced by DM Sans's `tnum` OpenType feature, applied globally
        // to .font-mono / .tabular-nums / numeric inputs in typography.css.
        sans:    ['"DM Sans"', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
        heading: ['"DM Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono:    ['"DM Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 4px)',
        sm: 'calc(var(--radius) - 8px)',
        xl: 'calc(var(--radius) + 4px)',
        '2xl': '1.5rem',
        '3xl': '1.75rem',
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))'
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))'
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))'
        },
        success: {
          DEFAULT: 'hsl(var(--success))',
          foreground: 'hsl(var(--success-foreground))'
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          foreground: 'hsl(var(--warning-foreground))'
        },
        border: 'hsl(var(--border) / 0.08)',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        chart: {
          '1': 'hsl(var(--chart-1))',
          '2': 'hsl(var(--chart-2))',
          '3': 'hsl(var(--chart-3))',
          '4': 'hsl(var(--chart-4))',
          '5': 'hsl(var(--chart-5))'
        },
        nq: {
          bg: '#07091c',
          card: 'rgba(255, 255, 255, 0.04)',
          'card-solid': '#0d1230',
          glass: 'rgba(255, 255, 255, 0.04)',
          brand: '#4F8CFF',
          'brand-light': '#6DA1FF',
          'brand-dark': '#2C5BFF',
          'brand-glow': 'rgba(79, 140, 255, 0.40)',
          'brand-tint': 'rgba(79, 140, 255, 0.14)',
          accent: '#4F8CFF',
          'accent-glow': 'rgba(79, 140, 255, 0.40)',
          violet: '#7B5BFF',
          'violet-glow': 'rgba(123, 91, 255, 0.32)',
          'violet-bright': '#A989FF',
          'violet-deep': '#5B36E0',
          blue: '#4F8CFF',
          'blue-light': '#6DA1FF',
          'blue-deep': '#2C5BFF',
          'blue-glow': 'rgba(79, 140, 255, 0.40)',
          'blue-tint': 'rgba(79, 140, 255, 0.14)',
          indigo: '#4F8CFF',
          'indigo-bright': '#6DA1FF',
          'indigo-deep': '#2C5BFF',
          'indigo-tint': 'rgba(79, 140, 255, 0.14)',
          cyan: '#5BC7FF',
          'cyan-tint': 'rgba(91, 199, 255, 0.14)',
          emerald: '#3FDD8A',
          red: '#FF5C7A',
          warn: '#FFB454',
          'border': 'rgba(255, 255, 255, 0.07)',
          'border-highlight': 'rgba(255, 255, 255, 0.12)',
          'text-primary': '#F1F5FF',
          'text-secondary': '#B8C0DA',
          'text-muted': '#7A82A5',
          'text-subtle': '#4A537A',
        }
      },
      boxShadow: {
        'card': '0 4px 20px rgba(0,0,0,0.15)',
        'card-hover': '0 8px 30px rgba(0,0,0,0.20)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' }
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' }
        },
        'glow-pulse': {
          '0%, 100%': { opacity: '0.15' },
          '50%': { opacity: '0.25' }
        },
        'chart-draw': {
          from: { strokeDashoffset: '1000' },
          to: { strokeDashoffset: '0' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'glow-pulse': 'glow-pulse 4s ease-in-out infinite',
        'chart-draw': 'chart-draw 2s ease-out forwards'
      }
    }
  },
  plugins: [require("tailwindcss-animate")],
};
