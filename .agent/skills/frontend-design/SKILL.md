---
name: frontend-design
description: Change Milano Sensual Congress layouts, styling, navigation, and responsive behavior within the existing homepage brand and performance requirements.
---

# Site design

Read `AGENTS.md`, `.agent/rules/brand-coherence.md`, and
`.agent/rules/performance.md`. Inspect `index.html`, `it/index.html`,
`tailwind.config.js`, and `css/fonts.css` before choosing components.

Reuse the dark navy palette, pink/purple accents, Inter body text, Playfair
Display headings, rounded CTAs, and existing navigation/footer. Keep layout
changes proportional to the issue; do not redesign for novelty or introduce
another stack. Use plain HTML/CSS and small JS only where behavior needs it.

Implement and inspect both languages at 375, 768, and 1440px. Let navigation
breakpoints follow the space its links actually need. Check logo proportions,
text wrapping, tap targets, keyboard focus, reduced motion, and horizontal
overflow. Test open menus and controls as well as the initial screen.

After class/CSS changes, follow the performance rule's build and critical-CSS
steps, then the static/browser/Lighthouse gates. Preserve content and metadata
unless the task requires changes; style edits do not reset article dates.
