# Official Milano Sensual Congress logo

Approved by the owner on 25 September 2026 for the website, presentations,
videos, and future congress materials. This replaces the old rectangular logo
and earlier proposed color-flex SVG concepts.

The unchanged 4096 × 4096 source is
`milano-sensual-congress-official-logo-source.png`. Its artwork and background
are opaque; black is part of the supplied raster. The source has not been
traced, redrawn, recolored, or regenerated with AI.

Run `python3 scripts/build_official_logo.py` from the repository root to
reproduce the cropped and optimized website, icon, and social-preview copies.
The crop removes only empty outside padding. All copies preserve aspect ratio.
The navigation derivative keys the neutral black matte to alpha so it works
on translucent glass headers. It retains the original colored artwork; it is
not redrawn. Navigation and motion overlays use screen compositing. The large
master, social cards and icons retain the supplied black backing.

Use `../milano-sensual-congress-official-logo.webp` for larger overlays and
`../milano-sensual-congress-official-logo-nav.webp` for navigation. Prefer
the full wordmark whenever space allows. Do not restore the retired assets as
fallbacks or treat historical exports as new logo references.
