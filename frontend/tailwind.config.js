/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        rf: {
          bg: '#0a0d14',
          panel: '#101522',
          panelBorder: '#1c2438',
          card: '#141b2d',
          accent: '#00f0ff',
          accentGlow: 'rgba(0, 240, 255, 0.25)',
          green: '#00ff88',
          greenGlow: 'rgba(0, 255, 136, 0.25)',
          amber: '#ffaa00',
          amberGlow: 'rgba(255, 170, 0, 0.25)',
          red: '#ff3366',
          purple: '#9d4edd',
          muted: '#64748b',
          text: '#f1f5f9',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scanline': 'scanline 8s linear infinite',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(1000%)' },
        }
      }
    },
  },
  plugins: [],
}
