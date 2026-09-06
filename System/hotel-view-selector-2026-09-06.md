# Hotel view selector — 6 September 2026

For the later removal of hotel website links, revised booking copy and current verification, see [Hotel booking copy update](hotel-booking-copy-2026-09-06.md). The measurements below record the original selector implementation.

The English and Italian hotel pages have separate views for the two hotels. A normal visit opens Event Hotel / Devero. Selecting Second Hotel replaces the hotel content with AS Hotel Cambiago's hero, photograph, address, facilities, two-night rates, booking link and assistance contacts. The selector remains visible below the navigation while scrolling.

## Behavior and implementation

- Native, labelled radio controls select the views, including when JavaScript is disabled. The page retains one visible main heading and the existing hidden breadcrumb trail.
- A short horizontal transition accompanies changes. Visitors can click the labels, use keyboard arrows, swipe the content, or slide the selector on touch devices. Reduced motion disables the transitions. Gallery gestures, vertical scrolling, interactive controls and browser edge gestures are excluded from page swipes.
- Inactive content is removed from layout and marked inert for assistive technology. The page height follows the selected hotel, with no empty space left for the other view.
- Direct AS Cambiago links and language changes retain the selected hotel; normal hotel URLs default to Devero. Back/forward navigation restores the selected view. View hashes use separate names from DOM panel IDs, so shared hotel links open at the top without automatic anchor scrolling.
- Shared styles are maintained in `css/hotel-views.css` and generated into both pages by `scripts/inline_critical_css.py`. `js/hotel-views.js` enhances the native controls. The Tailwind cache version is now 7 across the 65 referencing pages; critical CSS and generated indexes/twins are synchronized.
- The previous AS Cambiago addition's prices, dates, booking destinations, distance and sourced information are retained. See [the content/source report](as-cambiago-hotel-update-2026-09-06.md). Devero's gallery, venue description and FAQ remain within its own view. The availability and venue FAQ answers also match their JSON-LD.
- A small initial HTML bootstrap selects the requested hotel before its panels render and preloads that hotel's hero image. The English italic font is preloaded only for Devero, where it is used. AS cold-load checks confirm that Devero's hero and italic font are not downloaded. Native no-JavaScript use retains the Devero preload fallback.
- The Lighthouse runner accepts an optional fragment so the existing profiles can audit either view without altering throttling, third-party requests or audit selection.

## Browser and static verification

All checks were run against local files. Bookings and real form submissions were not sent.

- Master static gate: PASS. Node form/analytics/quality tests: 40/40 PASS. Python quality tests: 9/9 PASS.
- Full browser run: 839/846 initially passed across 69 pages and behavioral cases. Six hotel failures exposed WebKit dropping the `:focus-visible` state after native radio arrow navigation; the visible label now uses the radio's actual focus state. One separate WebKit phone ticket-reminder test timed out.
- Final hotel suite after all refinements: **72/72 PASS**, covering both languages, both views, exact booking links/rates, page height, keyboard focus, history, translated links, reloads, no-JavaScript operation, swipe guards, rapid switches and reduced motion in all nine browser/viewport combinations. Direct and translated hotel links verify a zero scroll position and check the initial asset requests, so the full page heading is visible on arrival and the inactive hotel's hero is not fetched.
- The isolated ticket reminder test passed **3/3 consecutive reruns** without changing form code or its assertion. Its initial timeout remains recorded as a test warning, rather than claiming a clean full-suite run.
- Both views and AS room cards were visually inspected in both languages at 375, 768 and 1440 px. The selector remained at 72 px below the viewport top while scrolling. An additional Chromium CDP touch gesture selected AS Cambiago on an emulated phone; cross-engine gesture guard checks use synthetic touch events.
- Evidence: `.quality/hotel-slider-full-browser-results.json`, `.quality/hotel-slider-first-browser-artifacts/`, `.quality/hotel-slider-final-views-results.json`, `.quality/hotel-slider-reminder-recheck-results.json`, and `.quality/hotel-slider-preview/`.

## Performance verification

Both views meet the required 95 minimum across all 12 page/view/profile pairs. Performance below uses the median, with the observed range in parentheses. Accessibility, Best Practices and SEO are **100 in every final run**.

| Hotel view / language | Phone performance | Tablet performance | Desktop performance |
| --- | ---: | ---: | ---: |
| Devero · EN | 96 (96–96) | 96 (96–96) | 100 (100–100) |
| Devero · IT | 97 (97–97) | 98 (98–98) | 100 (100–100) |
| AS Cambiago · EN | 95 (95–95) | 95 (95–95) | 100 (100–100) |
| AS Cambiago · IT | 95 (95–96) | 95 (94–95) | 100 (100–100) |

The final 28 raw reports (Devero: 10; AS Cambiago: 18) were collected serially on the same source fingerprint, with normal network/throttling settings and external services enabled. AS Cambiago was repeated three times for every profile; the default view used the runner's automatic repetition for marginal scores. One Italian AS tablet run scored 94; its three-run median is 95, meeting the specified aggregation rule with limited performance margin.

Auditing the direct AS link exposed browser anchor scrolling and a Lantern `NO_LCP` warning. Removing the automatic scroll restored the measurement. Subsequent repeated measurements and cold-load browser checks also exposed loading of Devero's unused assets; the initial selection and conditional preloads resolved that competition. Final reports contain no `NO_LCP` warning. Intermediate reports remain separate from final evidence.

Final raw JSON/HTML, manifests and summaries: `.quality/hotel-slider-event-verified/` and `.quality/hotel-slider-second-verified/`. Combined summary: `.quality/hotel-slider-verified-summary.json`. All dates, actual local URLs, browser versions and device profiles are retained in those reports.

`git diff --check`: PASS.

## Scope and release

These are local lab checks. Playwright 1.63.0 uses Chromium 153.0.8010.12, Firefox 155.0 and WebKit 26.6; WebKit is not installed Safari or physical iOS. Lighthouse 13.4.1 uses Chrome 152 and Node 26.7.0. Its tablet profile is Chrome emulation, not a physical iPad. No physical-device, live-site, real-user Core Web Vitals or fresh full-site Lighthouse measurement is claimed.

The build's existing outdated `caniuse-lite` notice and the browser runner's color-environment warning do not prevent checks from running. Dependencies, forms, analytics and release scope were not changed.

The changes remain local and uncommitted on `codex/website-quality-95`. The three pre-existing unpublished commits listed in the content/source report are preserved; no push, pull request, merge or deployment was performed. Local preview: http://127.0.0.1:4175/hotel (Devero by default), with `#as-hotel-cambiago` for the second hotel.
