# AS Hotel Cambiago addition — 6 September 2026

This report records the initial content addition. The subsequent split into two hotel views and its latest verification are documented in [Hotel view selector](hotel-view-selector-2026-09-06.md); the layout and scores below predate that follow-up.

The English and Italian hotel pages now offer AS Hotel Cambiago alongside Devero Hotel. The addition includes an availability notice at the top, an exterior photograph, the address and hotel facilities, a room-price table, and the supplied booking link. All congress activities remain explicitly located at Devero. Its existing booking destination, rates, event dates, ticket offers, assistance contacts, forms and analytics are preserved.

## Content and sources

- [AS Hotels official page](https://www.ashotels.it/as-hotel-cambiago): hotel name, four-star classification, address (Viale delle Industrie snc, 20040 Cambiago MI), free parking, restaurant, wellness and fitness facilities. The page was retrieved on 6 September 2026.
- [Event booking page](https://atmosferaeventi.it/prenotazione/134-5LAWjvWM-nZyIV9Cv-7gKm61tZ-AyoT1uNJ): the live room options match the supplied screenshot: double/twin €260 and single €220, with breakfast, for the 20–22 November 2026 stay. Displayed as totals per room for two nights. Existing booking-system typos in the room names and dates were not copied to the website. No booking was submitted.
- The approximately 800 m walking distance and limited remaining availability at Devero come from the user's event information; the walking route was not independently measured.
- [TUI hotel listing](https://www.tui.com/hotels/as-hotel-cambiago-128566/hotelinformation/): exterior photograph found through image search. [Original photo](https://pics.tui.com/pics/pics1600x1200/tui/0/001d84de33cb6bd91b1a0eff1983682d_ocpprod.jpg). The page includes a source credit. The original JPEG stays outside Git; the site uses genuine WebP files at 480, 800, 1200 and 1600 pixels without upscaling.

## Implementation

- Changes are in `hotel.html` and `it/hotel.html`; the stale January booking-opening FAQ is replaced in both visible content and matching JSON-LD. Metadata now describes both hotels, and AS Hotel Cambiago has a connected Hotel entity in each page's existing graph.
- Navigation, hidden breadcrumbs, visual identity and the Devero venue content remain in place.
- The new image's rendered widths were measured at 277 / 654 / 567 px for the 375 / 768 / 1440 px viewports. The responsive-image generator has a dedicated rule for this card.
- The final photo's low fetch priority prevents it competing with the main content. The existing Devero hero image is preloaded because Lighthouse identified it as the LCP image. The English hero's existing italic font is also preloaded; the Italian hero does not use that face.
- The compiled Tailwind stylesheet was rebuilt and its shared cache version advanced from 5 to 6 on 65 referencing pages. Their critical CSS was regenerated. Other pages' content is unchanged; the social metadata generator also repositioned existing favicon links in four heads without changing their values.
- Social metadata, both Markdown twins, feeds, sitemap and LLM indexes were regenerated with the project tools. The current compiled stylesheet was checked against a fresh build and matches byte for byte.

## Verification

All results below are local lab measurements, not live-site scores.

- Master static gate: PASS, no reported warnings.
- Node form/analytics/quality tests: 40/40 PASS.
- Python quality-gate tests: 9/9 PASS.
- Full browser suite: 774/774 PASS across all 69 pages and additional behavior cases, in Chromium, Firefox and WebKit at phone, tablet and desktop sizes. After the photo and loading refinements, both final hotel pages were retested in all nine browser/viewport combinations: 18/18 PASS.
- An intermediate focused run also passed 36 hotel/booking-guide browser checks after the photo replacement.
- Six additional hotel checks with JavaScript disabled verified keyboard section links, exact booking destinations, image decoding and no horizontal overflow. Both languages were visually reviewed at 375, 768 and 1440 px.
- `git diff --check`: PASS.

Lighthouse 13.4.1, Chrome 152, Node 26.7.0; Playwright 1.63.0 with Chromium 153.0.8010.12, Firefox 155.0 and WebKit 26.6. Lighthouse ran serially after browser testing, using the project's normal phone/tablet/desktop profiles and unmodified network/throttling settings. Repetitions were performed automatically for marginal results. The final audit has 10 raw reports across six page/profile pairs and zero failures.

| Page | Profile | Before performance | Final performance (range) | Accessibility | Best practices | SEO |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| hotel.html | phone | 96 | 95 (95–95) | 100 | 100 | 100 |
| hotel.html | tablet | 98 | 96 (96–96) | 100 | 100 | 100 |
| hotel.html | desktop | 100 | 100 (100–100) | 100 | 100 | 100 |
| it/hotel.html | phone | 98 | 97 (97–97) | 100 | 100 | 100 |
| it/hotel.html | tablet | 98 | 97 (97–97) | 100 | 100 | 100 |
| it/hotel.html | desktop | 100 | 100 (100–100) | 100 | 100 | 100 |

Performance values use the runner's median; other categories use its lowest result. The original English phone median was 96 (range 96–97). All final pairs meet the required 95 minimum. The first photo triggered a tablet image-resolution warning; replacing it and correcting loading priorities resolved the warning and the resulting tablet load delay. The final English phone score is exactly 95, so the result has limited performance margin.

Tooling warnings: the pinned build emits an outdated `caniuse-lite` notice; npm also noted an unapproved optional `fsevents` install script. Dependency installation completed with zero reported vulnerabilities and all required tooling ran successfully. Dependencies were not upgraded incidentally.

Lighthouse's tablet profile is Chrome emulation, not a physical iPad. Playwright WebKit is not installed Safari or physical iOS. No physical-device, live-site, real-user Core Web Vitals, or new full-site Lighthouse run was performed for this content update; Lighthouse coverage here is the two changed hotel pages. Tests did not send bookings or real leads. A release still needs the project's full CI deployment gates.

## Evidence and release state

- Initial reports: `.quality/as-cambiago-before/`.
- Final reports: `.quality/as-cambiago-verified/` (raw JSON, HTML, manifest and summary).
- Full browser report: `.quality/as-cambiago-full-browser-results.json`.
- Final hotel browser report: `.quality/browser-results.json`.
- Visual evidence and extra checks: `.quality/as-cambiago-preview/`.
- Local review: http://127.0.0.1:4175/hotel#as-hotel-cambiago and http://127.0.0.1:4175/it/hotel#as-hotel-cambiago.

The update is local and uncommitted on `codex/website-quality-95`. That branch already had three unpublished commits before this task: `d2ee3ad` (sitewide quality gates), `81677e5` (Meta diagnostic image transport), and `a3c83a2` (packaging verification and quality reports). Remote `main` was verified at `3c41f838298917272051720116e60f4b1298ef70`. No remote push, pull request, merge or deployment was performed. Publishing the combined branch requires a release-scope decision; the earlier work was preserved.
