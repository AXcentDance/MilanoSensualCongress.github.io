# Hotel booking copy — 6 September 2026

The English and Italian AS Cambiago room cards now direct visitors to the congress booking portal with “Book here” / “Prenota qui”. Hotel website links have been removed from the visible pages and the optional Hotel entity URL. The other sourced hotel facts, room prices and booking destinations are retained.

The new English copy is: “Our congress rates are lower than those on Booking.com or offered directly by the hotel.” The Italian copy is: “Le nostre tariffe per il congresso sono più basse di quelle su Booking.com o offerte direttamente dall’hotel.” This comparison is the organizer's statement supplied in the current request; a separate comparison of live public rates was not performed.

Existing styles were reused. Tailwind was rebuilt, its shared cache version advanced to 8 on 65 referencing pages, and critical CSS and generated metadata/indexes/Markdown twins were synchronized. Existing changes to project rules, CI and quality tooling were preserved.

The first Lighthouse pass measured an Italian AS view tablet Performance median of 94 (94–95 range). The decorative AS hero was therefore resized and encoded separately at 1000×750: 62,224 bytes instead of 118,556 bytes, a 47.5% reduction. Its preload and CSS background now use this smaller asset. The original room-card photos are retained. The optimized hero was visually inspected at all three widths, and the complete hotel browser suite was rerun successfully against the final files.

## Verification

- Master static gate: PASS.
- Node form, analytics and quality tests: 41/41 PASS.
- Existing hotel browser suite: 72/72 PASS in Chromium, Firefox and WebKit at 375, 768 and 1440 px, covering both languages, default/second views, keyboard and touch logic, direct links, initial asset loading and no-JavaScript operation.
- Six additional rendered checks verified the translated comparison, absence of hotel website links, exact portal destination and no horizontal overflow. Screenshots were visually inspected in both languages at all three widths.
- `git diff --check`: PASS. No bookings, leads or external messages were sent.
- Browser evidence: `.quality/hotel-rate-copy-browser-results.json`; visual evidence: `.quality/hotel-rate-copy-preview/`.

Final Lighthouse checks pass for both views in both languages at phone, tablet and desktop sizes. The 16 raw reports cover 12 page/view/profile combinations. Both audit summaries are complete and share the same final source hash. Performance scores below are medians; the range and run count are included where the runner repeated a marginal result. Accessibility, Best Practices and SEO each scored 100 in every run.

| View | Language | Phone | Tablet | Desktop |
| --- | --- | --- | --- | --- |
| Event Hotel | English | 96 (96–96, 3 runs) | 96 (96–96, 3 runs) | 100 |
| Event Hotel | Italian | 97 | 97 | 100 |
| AS Cambiago | English | 97 | 97 | 100 |
| AS Cambiago | Italian | 98 | 97 | 100 |

Unannotated scores are single runs, as required by the runner for initial Performance scores of at least 97 with no other category failure. All final measured CLS values were 0. Raw JSON and HTML evidence is in `.quality/hotel-rate-copy-event-verified/` (10 reports) and `.quality/hotel-rate-copy-second-verified/` (6 reports). The earlier tablet failure is retained in `.quality/hotel-rate-copy-second/` and is superseded by the audits after the image optimization.

These are local checks. Playwright 1.63.0 uses Chromium 153.0.8010.12, Firefox 155.0 and WebKit 26.6; WebKit is not installed Safari or physical iOS. Lighthouse 13.4.1 uses Chrome 152 and Node 26.7.0. The tablet profile is Chrome emulation. Physical devices, live-site performance, real-user Core Web Vitals and a fresh full-site browser/Lighthouse run are outside this copy update's measured coverage. The build's existing `caniuse-lite` notice and the browser runner's color-environment warning remain tooling warnings.

The changes are local. This task did not push, merge or deploy them. Preview: http://127.0.0.1:4175/hotel#as-hotel-cambiago.
