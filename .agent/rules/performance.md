---
trigger: always_on
---

# Performance and browser quality

## Measured acceptance

Target at least 95/100 in each Lighthouse category: Performance, Accessibility,
Best Practices, and SEO, on every indexable English and Italian page. Run the
pinned tooling with `npm ci` (Node 22.19+), then:

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
Audit switchable primary-content views through their direct URLs as well;
the second hotel view above is also enforced by CI.

Lighthouse acceptance and score tables cover indexable pages only. Skip
intentionally non-indexed utility/error pages, including `404.html`, unless the
user specifically requests an audit of them. Preserve their correct noindex
behavior. Scores cannot guarantee every browser, network,
future dependency version, real-user Core Web Vitals, or complete accessibility.

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
  Keep self-hosted WOFF2, `font-display: swap`, and metric-adjusted fallbacks.
- Keep `css/fonts.css`, compiled Tailwind **3.4.17**, and the Font Awesome subset.
  No runtime Tailwind CDN or external font/icon CDN. Existing approved form and
  analytics integrations are separate from this static-asset rule.
- After Tailwind class changes, run `npm run build:css`. If the compiled CSS
  bytes changed, bump its shared `?v=` consistently on every referencing page;
  otherwise retain the version. Then regenerate critical CSS. Reusing an
  already compiled utility does not require invalidating every page's cache.
- After a new Font Awesome icon, run `python3 scripts/build_fontawesome_subset.py`
  (fonttools + brotli), bump its asset version, and regenerate critical CSS.
- After HTML class changes or any source stylesheet changes, run
  `python3 scripts/inline_critical_css.py`. Generated `data-critical` and
  `data-inline` blocks are not edited by hand. Register a standalone page's
  stylesheet in that script's `PAGES` mapping when applicable.
- New photographic content uses bounded WebP variants through
  `generate_responsive_images.py` and `apply_responsive_images.py`; never upscale
  a smaller source merely to make every variant. Measure `sizes` at 375, 768,
  and 1440px before changing the generator's values.
- Keep full-length originals out of Git. Use compressed, capped-bitrate video
  with a WebP poster (the existing hero is 720p, about 1.5 Mbps). Decorative
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
