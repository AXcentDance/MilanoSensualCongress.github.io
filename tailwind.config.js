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
        brand: {
          dark: '#0f172a',
          purple: '#4c1d95',
          pink: '#be185d',
          accent: '#f43f5e',
          gold: '#fbbf24',
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
