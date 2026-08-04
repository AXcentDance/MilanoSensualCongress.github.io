# Agent Instructions

These instructions are mandatory for any AI agent working in this repository.

## First Step

Before answering with a plan or making any code, content, SEO, design, form, image, metadata, or structural change:

1. Inspect `.agent/rules/`.
2. Inspect `.agent/skills/`.
3. Apply every relevant rule and skill to the current task.

Do not treat `.agent` files as optional references. They are the canonical project instructions for this website.

## Always-On Project Rules

- Apply website changes equivalently to both the English and Italian versions whenever a matching page or flow exists.
- Act as a senior SEO expert and web designer for a bachata congress website.
- Prioritize Google discoverability, AI crawler clarity, international audience reach, and conversion to ticket buyers.
- For every new generated or added image, use descriptive lowercase hyphenated filenames, prefer WebP, and write natural language-specific alt text aligned with Bachata congress search intent.
- When adding a new page or significantly changing metadata/content, regenerate:
  - `sitemap.xml`
  - `llms.txt`
  - `llms-full.txt`
- For questions or requests that need planning, present the implementation plan first and ask before changing files, unless the user has already explicitly asked to make the change.

## Required Skill Checks

Use the relevant `.agent/skills/*/SKILL.md` instructions before working:

- `news-seo`: required for news articles, blog posts, timeline updates, and article SEO.
- `sync-indexes` and `site_metadata_sync`: required after adding pages or changing important metadata/content.
- `schema-graph`: required for schema, metadata, SEO page work, and new pages.
- `frontend-design` or `ui-ux-designer`: required for visual/layout/interface changes.
- `audit`: required for SEO audits or site health analysis.
- `find-keywords`: required for keyword research or targeting strategy.

## Verification Expectations

After any change, run the master gate (it absorbs the individual audit scripts
and enforces the site-wide invariants — CSP presence, speculation rules,
theme-color, canonical uniqueness, unique titles, sitemap coverage):

```bash
python3 scripts/run_all_checks.py
```

Individual checkers remain available (`scripts/check_html_syntax.py`,
`audit_links.py`, `audit_schema.py`, `audit_hreflang.py`, `audit_og.py`,
`audit_headings.py`, `check_image_seo.py`). CI runs the master gate on every
push and PR (`.github/workflows/site-checks.yml`), then regenerates
`sitemap.xml` + `llms*.txt` and pings IndexNow with changed URLs.

Report any checks that could not be run, and do not hide pre-existing failures.

## Self-Hosted Asset Invariants (do not regress)

- **No third-party CDNs.** Tailwind is compiled statically: after adding or
  changing Tailwind classes, rebuild with
  `npx tailwindcss@3.4.17 -c tailwind.config.js -o css/tailwind.min.css --minify`
  and bump the `?v=` query on every page in the same change set.
- **Font Awesome is subset.** After using a NEW icon, run
  `python3 scripts/build_fontawesome_subset.py` (requires `fonttools`+`brotli`).
- **Fonts are self-hosted** in `/fonts` via `css/fonts.css`. Never reintroduce
  fonts.googleapis.com / cdnjs / cdn.tailwindcss.com — the per-page CSP will
  block them anyway.
- **Responsive images.** New content images get 480/800/1200 WebP variants
  (`python3 scripts/generate_responsive_images.py`) and srcset/sizes via
  `scripts/apply_responsive_images.py`. `sizes` values in that script were
  measured in a real browser at 375/768/1440px — re-measure before changing.
- **Social metadata** is normalized by `python3 scripts/sync_social_meta.py`
  (og/twitter mirror title/description/canonical; og:image uses JPG cards in
  `images/og/`). Run it after adding pages or changing titles/descriptions.
- **Every page** must carry: one CSP meta, one canonical (or noindex), the
  speculation-rules block + `/js/prefetch-fallback.js`, theme-color, and the
  prerender-guarded Meta Pixel. The master gate fails otherwise.
- **Videos**: never commit progressive full-length originals; encode with
  capped bitrate (see `images/hero-720.mp4`, ~1.5 Mbps 720p) and use
  `preload="metadata"` with a WebP poster.
