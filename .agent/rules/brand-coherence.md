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

- **Official logo (owner approved 25 September 2026):** Use the supplied
  tricolor spires and pink/purple Milano Sensual Congress wordmark for the
  website, presentations, videos, and future congress materials. The rectangular
  logo is retired. The exact supplied source is
  `images/brand/milano-sensual-congress-official-logo-source.png`; web copies use
  the `milano-sensual-congress-official-` filenames. Rebuild size variants with
  `python3 scripts/build_official_logo.py`. Preserve the artwork, lettering,
  colors, and proportions. The older rectangular assets and color-flex SVG
  concepts are historical references, not current brand assets. See the
  [official logo notes](../../images/brand/milano-sensual-congress-official-logo-notes.md).

- **2027 edition direction (owner requested 26 September 2026):** “Milano,
  In Full Colour” replaces the prior edition's flows and purple gradients.
  Use the tokens in `css/edition-2027.css`: ink green `#062b27`, night green
  `#031c19`, warm ivory `#f4f0e6`, emerald `#1d785d`, vermilion `#c83e2b`,
  coral `#f38c78`, sage `#b6c7b8`, and restrained gold `#cfb989`.
  Dark editorial mastheads alternate with ivory reading and hospitality
  surfaces. Use darker vermilion for white-text buttons and coral for
  accents on green. Contrast and hierarchy, rather than claims about universal
  psychological effects, guide color choices. Keep the official logo colors.
- **Typography:** Use self-hosted Inter for body copy, navigation, and controls,
  and Playfair Display for display headings, following the homepage's weights,
  scale, and use of italics. Do not introduce a different font pairing.
- **Navigation and footer:** Carry over the homepage's logo treatment, sticky
  navigation, mobile menu, language switcher, and footer styling. Adapt link
  paths and active states to the page and language; follow the
  [breadcrumb contract](breadcrumbs.md).
- **Buttons and controls:** Use the solid vermilion primary CTA, crisp 2px
  corners, ivory/outlined secondary buttons and underlined editorial links.
  Preserve generous touch targets and visible gold keyboard focus states.
- **Layout and surfaces:** Match the homepage's container widths, spacing
  rhythm, ruled editorial sections, portrait grids, and restrained hover
  effects. Avoid decorative glowing cards. Adapt content structure and reading
  width to the page's purpose while keeping this visual language recognizable.
- **Imagery and motion:** Keep imagery treatments, dark overlays, and animation
  consistent with the homepage. Preserve accessibility, reduced-motion support,
  and the project's performance requirements; do not copy effects that violate
  those requirements.

## Preview facts

The 2027 branch is a local edition preview. Dates and prices for 2027 have not
been supplied. Current artists, hotel, video and exact 2026 operational facts
are retained by request, with visible reference labels. Do not invent a 2027
event occurrence, redate archive articles, or label the existing 2026 checkout
as a 2027 sale. Replace reference content coherently when facts are confirmed.

## Precedence and verification

A separate visual identity requires an explicit user instruction; use the
precedence in [AGENTS.md](../../AGENTS.md#precedence-and-scope).

Before considering a new page complete, compare it visually with the homepage
at mobile, tablet, and desktop widths (375, 768, and 1440px), and check equivalent
styling in both languages. Fix unintended differences in palette, typography,
navigation, buttons, and surfaces. Complete the shared
[delivery checks](delivery.md#verification-and-completion); automated checks do
not replace this visual comparison.
