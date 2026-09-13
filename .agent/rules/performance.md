---
trigger: always_on
---

# Performance and browser quality

## Measured acceptance

Target at least 95/100 in each Lighthouse category: Performance, Accessibility,
Best Practices, and SEO, on every indexable English and Italian page. For a
completed change set, run browser and Lighthouse checks on **affected pages**:
the changed pages plus every page or view whose rendering or behavior depends
on the changed assets, scripts, styles, navigation, or generated output. Include
translated counterparts and affected interaction states. Determine this scope
from references, dependencies and the actual output diff, not HTML filenames
alone. Keep all three device profiles; functional browser checks use all three
browser engines for affected behavior.

A homepage-only video change needs the English and Italian homepages; it does
not require auditing unrelated articles or hotel views. A font, stylesheet or
loader used throughout the site needs site-wide coverage. Inspect uncertain
dependencies first; use full coverage if their impact cannot be safely bounded.
Do not rerun unchanged, passing page checks without a relevant dependency change
or an explicit request for a fresh audit. A scoped pass covers only its stated
pages and views; do not present it as a new site-wide measurement.

Use the selectors in [focused iteration](#focused-iteration) for both iteration
and final checks of a bounded change. For a site-wide change or an explicitly
requested full-site audit, run the full commands below. Use the pinned tooling
(`npm ci` in a fresh environment, Node 22.19+):

```bash
npm run audit:lighthouse
npm run audit:lighthouse -- --pages=hotel.html,it/hotel.html --fragment=as-hotel-cambiago --output=.quality/lighthouse-as-hotel
npm run test:browser
```

For a fresh environment, install Python checker dependencies with
`python3 -m pip install -r requirements-dev.txt` and test browsers with
`npx playwright install --with-deps chromium firefox webkit`. Lighthouse also
needs an installed Chrome browser (or an explicit `CHROME_PATH`).

The Lighthouse runner covers phone, a custom 768×1024 tablet viewport using
mobile throttling, and desktop. Lighthouse uses Chrome; the tablet result is
not a real iPad measurement. Playwright separately covers Chromium, Firefox,
and WebKit at phone, tablet, and desktop widths. WebKit is not installed Safari
or physical iOS. State these limits in reports and record actual versions.

Keep raw reports, test date, URL/environment, profile, and scores. Audit pages
serially on an otherwise idle machine. Repeat marginal/failing results three
times and report the Performance median and range; use the lowest Accessibility,
Best Practices, and SEO result so intermittent defects cannot pass. Report
live and local results separately. Do not weaken throttling, hide audits, block
third parties, or detect Lighthouse to manufacture a passing score.
The runner does these repetitions automatically for initial performance below
97 or another failed category. `--runs 3` forces three runs for a specified
comparison. `--resume` requires unchanged sources and configuration.
Audit affected switchable primary-content views through their direct URLs as
well; include the second hotel view when hotel behavior or a shared dependency
affecting it changes, and in full-site audits. These commands discover pages
automatically when run; execution and publication follow
[delivery](delivery.md#verification-and-completion).

Lighthouse acceptance and score tables cover indexable pages only. Skip
utility/error pages approved by the shared
[`site_files.py` policy](../../scripts/site_files.py), unless the user specifically
requests an audit of them. Affected utility/error pages still receive functional
browser checks; full browser runs cover all public HTML.
Preserve their correct noindex behavior. Scores cannot guarantee every browser, network,
future dependency version, real-user Core Web Vitals, or complete accessibility.

## Focused iteration

Use `npm run test:browser -- --list` to find the actual test names and projects,
then select the affected cases with `--grep` and, during diagnosis when useful,
`--project`. Include the translated page and affected interaction states. Final
coverage includes all three browser engines and device widths for those cases;
a single diagnostic project does not replace them.
For a performance investigation, select explicit pages:

```bash
npm run audit:lighthouse -- --pages=hotel.html,it/hotel.html --output=.quality/lighthouse-focused
```

Keep the measured-acceptance settings, thresholds and repeat policy. During
iteration, representative affected layouts can shorten feedback. Final checks
cover every affected page/view identified above, not merely a sample. Generator
changes require checking their affected outputs; an output used throughout the
site expands coverage accordingly. Another instruction linking here does not
require a duplicate passing run.

## Render and load

- Keep main content in HTML and readable with JavaScript disabled. Keep the
  navigation and LCP heading/image visible from first paint; never animate
  their opacity from zero. Optional secondary reveals must respect reduced
  motion and must not delay LCP.
- Keep dimensions/aspect ratios on media. Load above-fold images eagerly and
  reserve `fetchpriority="high"` for the actual LCP image; lazy-load below-fold content images. A small
  navigation logo should load eagerly and must not shrink out of proportion.
- CSS background images can also be LCP. Use a suitably bounded encoded asset
  and preload it when measurement shows it is critical. Check actual image
  encoding: a JPEG renamed to .webp has not been converted or optimized.
- Preload only font faces used above the fold, including italic when needed.
  Keep self-hosted WOFF2, `font-display: swap` for text fonts, and metric-adjusted
  text fallbacks. The small Font Awesome icon subset deliberately uses
  `font-display: block` to avoid rendering private-use codepoints as wrong glyphs
  while loading. Keep accessible names independent of icon fonts and verify
  this behavior in browser/Lighthouse checks after font changes.
- Keep `css/fonts.css`, compiled Tailwind **3.4.17**, and the Font Awesome subset.
  No runtime Tailwind CDN or external font/icon CDN. Existing approved form and
  analytics integrations are separate from this static-asset rule.
- After Tailwind class changes, run `npm run build:css`. If the compiled CSS
  bytes changed, bump its shared `?v=` consistently on every referencing page;
  otherwise retain the version. Then regenerate critical CSS. Reusing an
  already compiled utility does not require invalidating every page's cache.
- After a new Font Awesome icon, run `python3 scripts/build_fontawesome_subset.py`
  (fonttools + brotli), update its stylesheet version and changed font preloads,
  and regenerate critical CSS. Generated font filenames include their content
  hash; retain older font files while cached pages may still reference them.
- After HTML class changes or any source stylesheet changes, run
  `python3 scripts/inline_critical_css.py`. Generated `data-critical` and
  `data-inline` blocks are not edited by hand. Register a standalone page's
  stylesheet in that script's `PAGES` mapping when applicable.
- New photographic content uses bounded WebP variants through
  `generate_responsive_images.py` and `apply_responsive_images.py`; never upscale
  a smaller source merely to make every variant. Measure `sizes` at 375, 768,
  and 1440px before changing the generator's values.
  The generator owns source/recipe/output hashes in `.quality/responsive-images.json`;
  a missing cache rebuilds verified derivatives. Run generation before applying
  HTML variants. After shrinking a source, the generator refuses to remove a
  derivative that HTML or CSS still uses and lists its references. First run the
  applier to prune standard sets; review any remaining custom crop/picture/CSS
  references explicitly, then rerun generation and application. Custom choices
  must not be silently overwritten. Missing tools, unreadable images or failed conversions stop the
  build and preserve prior outputs; resolve the error instead of accepting a
  partial build. Image builds require ffmpeg/ffprobe and WebP tools; do not restore
  retired bulk image mutators.
- Keep full-length originals out of Git. Use compressed, capped-bitrate video
  with a WebP poster. For broad phone compatibility, use 8-bit H.264 (`yuv420p`),
  an appropriate profile/level, and MP4 faststart; do not inherit a source's
  10-bit H.264 format. Verify actual autoplay and advancing playback in WebKit
  as well as Chromium and Firefox. Decorative
  video may use `preload="none"` and delayed source attachment; user-requested
  content video may use `preload="metadata"`. Respect reduced motion/data saving.
- Defer optional analytics/decorative code to idle after load, retain the
  prerender guard and essential event tracking, and measure actual CPU/network
  impact. An idle callback alone does not prove the work is free.

## Interaction and safety

Use semantic controls with accessible names, labels, visible keyboard focus,
sufficient contrast, and generous touch targets (aim for 44×44px for standalone
controls). Menus must fit their content at tablet widths, open with keyboard
and touch, and expose their state. Keep useful content available without JS.
Use optional transform/color transitions and reduced-motion fallbacks; static
interfaces are valid. Do not add mandatory motion or `transition-all`.

Keep one CSP meta, theme color, canonical/intentional noindex, speculation rules,
prefetch fallback, and the shared analytics loader on each page. Permit only
verified integration origins in CSP. Do not suppress console errors to pass.
Test links, menus, language switches, FAQ controls and forms; stub external form
submissions in tests so tests do not send messages, bookings, or real leads.
