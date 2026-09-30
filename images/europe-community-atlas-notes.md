# Europe community atlas

Orthographic decorative land outline centred on Europe, derived from Natural Earth 1:110m land data (public domain), retrieved 28 September 2026.

- Source: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson
- Terms: https://www.naturalearthdata.com/about/terms-of-use/
- Projection: orthographic, centre 50° N / 20° E; scale 610; origin (400, 320) in an 800 × 620 viewBox.
- Land polygons simplified in projected coordinates to 0.65px tolerance.
- Connection points use representative capital locations, with Milano at 45.4642° N, 9.19° E, projected to (319.76, 362.42). The curves represent a shared community, not booked transport routes or measured attendee origins.

Country names and flags are available as HTML independently of the decorative map.

## Visual treatments

- `europe-community-atlas.svg` preserves the original muted, dotted treatment and the source geometry.
- `europe-community-sculpted-emerald.svg` implements the owner-selected **01 · Sculpted emerald** direction, approved on 28 September 2026. It reuses the original land and graticule paths, projection and 800 × 620 frame without changing the connection coordinates.
- The sculpted land uses the approved emerald gradient (`#1c4937`, `#4c8260`, `#1f4c39`), a restrained `#bcbe89` coastline and a shallow 6px dark-green relief with a soft shadow. A subtle warm halo remains centred on Milano.
- Horizontal and vertical edge masks use the preview's fade stops, adapted to the complete frame so the surrounding geography fades while Europe remains legible. The dotted texture is removed.
- The selected SVG is self-contained, with reusable land paths, native SVG gradients, masks and a static shadow. It has no script, external image, font or runtime dependency. The page supplies the emerald background and accessible country controls independently.

### Caspian Sea correction

`europe-community-sculpted-emerald-coastlines.svg` corrects the Caspian Sea on 28 September 2026. The source's sole interior ring had been drawn as separate land; it now forms an even-odd hole within the Eurasia path, shared by the surface and relief layers. All other geometry, styling and coordinates are preserved, as are the earlier SVG assets.

### Phone country borders

On 29 September 2026 the owner requested thin borders between countries on the
phone map. `europe-community-sculpted-emerald-country-borders.svg` preserves the
corrected coastlines, relief, gradients and projection and adds fine warm-gold
land boundaries. Only the phone map uses this variant; desktop keeps the
coastlines asset. Pins and connection coordinates are unchanged.

- Boundary source: Natural Earth 1:110m Admin 0 land boundary lines, public domain,
  retrieved 29 September 2026. This is decorative small-scale geography.
- Pinned GeoJSON: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_110m_admin_0_boundary_lines_land.geojson
- SHA-256: `d42479fd79552cca4eec7f85fcdca717a790d29ff06be7676f1af0568c6d3f7c`
- Dataset overview: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-boundary-lines/
- Rebuild after downloading that source: `python3 scripts/build_phone_country_borders.py --source /path/to/ne_110m_admin_0_boundary_lines_land.geojson`.
- The build reuses the existing orthographic projection and clips through the
  SVG viewport. Boundaries are a static native SVG layer, with no client-side
  map library or extra request beyond the phone's existing lazy-loaded map.
