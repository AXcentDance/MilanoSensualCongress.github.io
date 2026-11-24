/**
 * Tailwind CLI config — replaces the former cdn.tailwindcss.com runtime config.
 * Build the static stylesheet with:
 *   npx tailwindcss@3.4.17 -c tailwind.config.js -o css/tailwind.min.css --minify
 * (Union of every inline `tailwind.config` block that previously shipped on the pages.)
 */
const { execFileSync } = require('node:child_process');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const pages = JSON.parse(execFileSync('python3', [resolve(__dirname, 'scripts/site_files.py')], { encoding: 'utf8' }));
module.exports = {
  // The same inventory as the quality gates includes future nested pages.
  // Generated inline CSS must not preserve classes removed from the actual HTML.
  content: [
    ...pages.map(file => ({ extension: 'html', raw: readFileSync(resolve(__dirname, file), 'utf8')
      .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '') })),
    './js/**/*.js',
  ],
  safelist: ['hidden', 'animate-spin'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Inter Fallback', 'sans-serif'],
        serif: ['Playfair Display', 'Playfair Display Fallback', 'serif'],
      },
      colors: {
        slate: { 50: '#f4f0e6', 100: '#f4f0e6', 200: '#e9e8dc', 300: '#d5e0d1', 400: '#b6c7b8', 500: '#819b89', 600: '#537664', 700: '#305448', 800: '#103b33', 900: '#062b27', 950: '#031c19' },
        pink: { 50: '#fff6f0', 100: '#fbe3d6', 200: '#f4d1bd', 300: '#f6b39f', 400: '#f38c78', 500: '#d65a43', 600: '#c83e2b', 700: '#a82f20', 800: '#822719', 900: '#542218', 950: '#311610' },
        purple: { 50: '#f1f6eb', 100: '#dfead8', 200: '#cfdfc7', 300: '#b6c7b8', 400: '#a6c8b1', 500: '#70a28b', 600: '#1d785d', 700: '#155b46', 800: '#134b3c', 900: '#103b33', 950: '#062b27' },
        indigo: { 50: '#f1f6eb', 100: '#dfead8', 200: '#cfdfc7', 300: '#b6c7b8', 400: '#a6c8b1', 500: '#70a28b', 600: '#1d785d', 700: '#155b46', 800: '#134b3c', 900: '#103b33', 950: '#062b27' },
        brand: {
          dark: '#062b27',
          purple: '#1d785d',
          pink: '#c83e2b',
          accent: '#f38c78',
          gold: '#cfb989',
        },
      },
      animation: {
        'fade-in-up': 'fadeInUp 1s ease-out forwards',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
};
