---
trigger: always_on
---

# Homepage visual identity is mandatory

Every new website page must follow the same style and color palette as the
homepage so that Milano Sensual Congress has one coherent visual identity.
This applies to all page types, including news articles, guides, landing pages,
and forms, and equally to the English and Italian versions.

## Source of truth

Before designing or creating a page, inspect `index.html`, `it/index.html`,
`tailwind.config.js`, and `css/fonts.css`. Reuse the current homepage's visual
patterns and shared assets. A subpage with a different aesthetic is not a brand
reference. If the user changes the homepage's brand direction, follow that
updated direction on subsequent new pages.

## Required visual language

- **Palette:** Preserve the dark navy base (`brand.dark`, `#0f172a`), white/slate
  text, and the homepage's pink, purple, and indigo accents. The shared brand
  tokens are purple `#4c1d95`, pink `#be185d`, accent `#f43f5e`, and gold
  `#fbbf24`; use gold sparingly as on the homepage. Reuse the homepage's existing
  shades, gradients, and transparency treatments rather than inventing a new
  palette or changing the page to a light theme.
- **Typography:** Use self-hosted Inter for body copy, navigation, and controls,
  and Playfair Display for display headings, following the homepage's weights,
  scale, and use of italics. Do not introduce a different font pairing.
- **Navigation and footer:** Carry over the homepage's logo treatment, glass
  navigation, mobile menu, language switcher, and footer styling. Adapt link
  paths and active states to the page and language, and retain hidden subpage
  breadcrumbs as required by `.agent/rules/breadcrumbs.md`.
- **Buttons and controls:** Reuse the rounded primary CTA with the homepage's
  pink-to-purple gradient (`135deg`, `#ec4899` to `#8b5cf6`) and hover gradient
  (`#db2777` to `#7c3aed`). Match existing secondary buttons, links, and dark
  translucent form fields, with accessible keyboard focus states.
- **Layout and surfaces:** Match the homepage's container widths, spacing
  rhythm, rounded cards, translucent dark surfaces, subtle light borders,
  shadows, and restrained hover effects. Adapt content structure and reading
  width to the page's purpose while keeping this visual language recognizable.
- **Imagery and motion:** Keep imagery treatments, dark overlays, and animation
  consistent with the homepage. Preserve accessibility, reduced-motion support,
  and the project's performance requirements; do not copy effects that violate
  those requirements.

## Precedence and verification

This project rule takes precedence over generic design-skill suggestions to
vary fonts, themes, palettes, or aesthetics between pages. Creativity must stay
within the homepage's brand system. A separate visual identity requires an
explicit user instruction.

Before considering a new page complete, compare it visually with the homepage
at mobile, tablet, and desktop widths (375, 768, and 1440px), and check equivalent
styling in both languages. Fix unintended differences in palette, typography,
navigation, buttons, and surfaces. Run `python3 scripts/run_all_checks.py` as
required by `AGENTS.md`; automated checks do not replace this visual comparison.
