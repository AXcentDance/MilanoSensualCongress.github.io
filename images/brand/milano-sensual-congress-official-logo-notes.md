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
master, social cards and historical full-logo icon retain the supplied black backing.
The dedicated arrows-only favicon below uses transparency.

Use `../milano-sensual-congress-official-logo.webp` for larger overlays and
the `../milano-sensual-congress-official-logo-nav_100w.webp`, `_200w.webp`,
and `_300w.webp` derivatives for navigation, with the existing 400 × 240
`../milano-sensual-congress-official-logo-nav.webp` retained for higher densities.
The live navigation displays the artwork at 93⅓ × 56 CSS pixels; its responsive
markup selects an adequate source for the device density without changing that
display size. All navigation exports use the same approved crop, Lanczos resize,
matte-to-alpha conversion and lossless WebP encoding. Prefer
the full wordmark whenever space allows. Do not restore the retired assets as
fallbacks or treat historical exports as new logo references.

## Arrows-only browser favicon

On 28 September 2026 the owner requested only the seven tricolour spires for
browser tabs, with the lower stems extended symmetrically. On 29 September the
owner selected a transparent background and requested publication. The favicon
has two green, three white and two red spires, stepped pyramid tops and a shared
lower baseline. It does not replace the full official wordmark elsewhere.

After reviewing the live tab icon on 29 September, the owner selected a medium
stem weight between the thin version and the bold preview and requested
publication. The medium artwork has less outside padding for tab legibility
while preserving seven separate spires and their colours. It uses the preserved
first thickened draft; the earlier thin assets remain available for cached pages.

The 1254 × 1254 RGBA source is
`milano-sensual-congress-tricolor-spires-favicon-medium-source.png`, adapted
from the official logo with the built-in image generation tool. It is a generated
adaptation, not a pixel-identical crop. Reproduce the 32px and 192px PNGs and the
16/32/48px root ICO with `python3 scripts/build_favicon.py`. Alpha-aware resizing
preserves transparent edges without a dark matte. All public pages reference
these dedicated files, so rebuilding the full logo cannot overwrite the favicon.
The white spires naturally blend into a pure-white tab background; the flag
colours remain unchanged.
