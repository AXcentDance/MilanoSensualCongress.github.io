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
the lossless `../milano-sensual-congress-official-logo-nav-2027.webp` responsive
family for the 2027 navigation. Its `sizes` is
`(max-width: 700px) 87px, 100px`, matching the existing navigation CSS.
The `_100w` and `_175w` copies reduce downloads at 1x and phone 2x density;
the unchanged 200px fallback and `_300w` copy cover desktop 2x and phone/desktop
3x density. Every derivative comes directly from the unchanged approved PNG
with the same crop and alpha key; lossless encoding preserves the resized
artwork's visible pixels and transparency. Retain the historical 400px
`../milano-sensual-congress-official-logo-nav.webp` for its larger uses. Prefer
the full wordmark whenever space allows. Do not restore the retired assets as
fallbacks or treat historical exports as new logo references.

## Arrows-only browser favicon

On 28 September 2026 the owner requested only the seven tricolour spires for
browser tabs, with the lower stems extended symmetrically. The dedicated
favicon has two green, three white and two red spires, stepped pyramid tops
and a shared lower baseline. On 29 September the owner requested removal of
the black backing: the current favicon has a genuinely transparent background.
It does not replace the full official wordmark elsewhere.

After inspecting the live tab icon on 29 September, the owner requested more
visible stems, then selected a weight between the thin live icon and the bold
preview. The current source is
`milano-sensual-congress-tricolor-spires-favicon-medium-source.png`, with medium
opaque stems and a larger footprint inside the transparent square. The seven
separate spires retain their flag colours, stepped tops and common baseline.
The built-in image generation tool adapted the official logo; this is not a
pixel-identical crop. The medium version uses the preserved first thickened
draft. Earlier thin, bold and black-backed sources remain historical
references. The thin transparent version was published in commit `6b43dd9a`;
the medium revision was published on 29 September 2026 in commit `18a33eef`.

Reproduce the 32px and 192px PNGs and the 16/32/48px root ICO with
`python3 scripts/build_favicon.py`. All public pages reference these dedicated
files under the `tricolor-spires-favicon-medium` basename, plus the root
ICO. Alpha-aware resizing preserves transparent edges without a dark matte.
The white spires naturally blend into a pure-white tab background; the flag
colours remain unchanged. The older `official-icon.webp` remains a historical full-logo export;
the official-logo builder cannot overwrite the new favicon.
