/**
 * Tailwind CLI config — replaces the former cdn.tailwindcss.com runtime config.
 * Build the static stylesheet with:
 *   npx tailwindcss@3.4.17 -c tailwind.config.js -o css/tailwind.min.css --minify
 * (Union of every inline `tailwind.config` block that previously shipped on the pages.)
 */
module.exports = {
  content: [
    './*.html',
    './it/*.html',
    './news/*.html',
    './it/news/*.html',
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
