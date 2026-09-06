# Hotel swipe image fix — 6 September 2026

Returning from AS Cambiago to Event Hotel briefly changed the crop of the Devero hero photo. The Devero background used `background-attachment: fixed`, while its parent hotel panel moved with a transform. The photo changed its positioning reference when that transform ended.

Both English and Italian Devero hero styles now use `background-attachment: scroll`, keeping the image attached to the sliding panel throughout the transition and after it settles. The slideshow behavior, photos, booking copy, rates, links, analytics and other pending work were retained. This CSS-only fix does not rebuild Tailwind or change editorial dates; critical CSS was regenerated and is fresh.

## Verification

- Reproduced the original crop jump at the reported 661×864 viewport: 41.16% of the hero pixels changed between the final transformed frame and the settled image, using a per-channel difference threshold of 8. The candidate fix eliminated that visible jump. Evidence: `.quality/hotel-swipe-preview/`.
- Captured and compared 48 final-frame/settled pairs: both swipe directions, both languages, Chromium/Firefox/WebKit, and widths 375, 661, 768 and 1440. Representative captures and the largest Firefox differences were visually inspected; the photo framing is stable. Chromium and WebKit comparisons have negligible pixel differences. Firefox retains text/edge rasterization differences (up to 2.16% of pixels), without the original image crop change. Evidence: `.quality/hotel-swipe-verified/`, including `frames.json` and `comparison.json`.
- Master static gate: PASS.
- Node form, analytics and quality checks: 41/41 PASS.
- Existing hotel browser suite: 72/72 PASS across Chromium, Firefox and WebKit at phone, tablet and desktop widths. Coverage includes isolated hotel content, keyboard selection, focus, language switching, direct links, history, swipe direction/scroll guards, rapid switching, reduced motion and no-JavaScript operation. Evidence: `.quality/hotel-swipe-browser-results.json`.
- No real form submissions, bookings, leads or external messages were sent. External requests were stubbed only in the browser behavior/visual checks; Lighthouse uses the unmodified page and normal network behavior.

Lighthouse passes in both views and both languages: 16 reports across 12 view/language/device combinations, with complete summaries sharing the same final source hash. Accessibility, Best Practices and SEO each scored 100 in every run, and every measured CLS was 0.

| View | Language | Phone Performance | Tablet Performance | Desktop Performance |
| --- | --- | --- | --- | --- |
| Event Hotel | English | 96 (96–96, 3 runs) | 96 (96–96, 3 runs) | 100 |
| Event Hotel | Italian | 97 | 98 | 100 |
| AS Cambiago | English | 97 | 97 | 100 |
| AS Cambiago | Italian | 97 | 97 | 100 |

Repeated Performance scores are medians with their ranges. Unannotated scores are single runs, following the runner's automatic repetition rule. Raw JSON/HTML evidence: `.quality/hotel-swipe-event/` (10 reports) and `.quality/hotel-swipe-second/` (6 reports). `git diff --check` also passes.

These are local checks. Playwright 1.63.0 uses Chromium 153.0.8010.12, Firefox 155.0 and WebKit 26.6; WebKit is not installed Safari or physical iOS. Lighthouse 13.4.1 uses Chrome 152 and Node 26.7.0. The tablet Lighthouse profile is Chrome emulation. Physical-device gestures, live performance, real-user Core Web Vitals and fresh full-site coverage were not measured in this narrow fix. The browser runner's existing `NO_COLOR` / `FORCE_COLOR` warning remains a tooling notice.

The fix is local and has not been pushed or deployed. Preview: http://127.0.0.1:4175/hotel#as-hotel-cambiago.
