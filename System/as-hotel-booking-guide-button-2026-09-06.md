# AS Cambiago Booking Guide button — 6 September 2026

The AS Cambiago hero now has the same outlined Booking Guide button as Event Hotel, including the information icon, rounded shape, border and hover colors. The English label is “Booking Guide”; the Italian label is “Guida alla Prenotazione”. The two hero buttons sit side by side when space permits and stack on narrower screens.

The new button links to `BookHotel#as-hotel-cambiago` in the current language. Because the existing guide only described Devero, both guide pages now identify the two hotels and include an AS Cambiago section with its correct congress reservation link and a return link to the second hotel view. Shared booking steps and assistance remain below it. The guide heading and description now cover both hotels; the existing canonical URLs and hidden breadcrumbs are retained.

The existing Tailwind utilities were reused. Rebuilding produced identical CSS bytes, so the shared version remains 8. Critical CSS, social metadata, Markdown twins, feeds, sitemap and AI indexes were regenerated. Prices, dates, existing reservation endpoints, forms and analytics were preserved.

## Verification

- Master static gate: PASS against the final files.
- Node form, analytics and quality tests: 41/41 PASS.
- Existing hotel and guide browser checks: 108/108 PASS, covering both languages, Chromium/Firefox/WebKit, and phone/tablet/desktop sizes. After shortening the new guide card's booking label to fit on mobile, the 18 guide-page checks were rerun and passed again.
- Eighteen additional button-to-guide-to-hotel flows pass across all three engines, both languages and widths 375, 768 and 1440. They verify the translated button, a touch target of at least 44 px, no horizontal overflow, the correct guide anchor and AS reservation endpoint, the existing Devero endpoint, and return to the second hotel view. Final hero and guide screenshots were inspected in both languages at all three widths.
- An early ad hoc WebKit Italian tablet return-link check had a timing failure. Three isolated repeats passed. The final visual routine waits for guide fonts and anchor scrolling to settle before checking the return link; all 18 final flows pass. No application behavior or test assertions were weakened to clear this result.
- Browser evidence: `.quality/hotel-guide-browser-results.json` and `.quality/hotel-guide-final-browser-results.json`. Visual/navigation evidence: `.quality/hotel-guide-button-preview/`, including `results.json`.
- No real form submissions, bookings, leads or external messages were sent. Browser behavior checks stub external requests; Lighthouse uses the unmodified page and normal network behavior.

Lighthouse passes for both hotel views and both guide pages in both languages. The 22 reports cover 18 page/view/profile combinations; both summaries are complete and share the same final source hash. Accessibility, Best Practices and SEO each scored 100 in every run.

| Page / view | Language | Phone Performance | Tablet Performance | Desktop Performance |
| --- | --- | --- | --- | --- |
| AS Cambiago | English | 97 | 97 | 100 |
| AS Cambiago | Italian | 98 | 97 | 100 |
| Event Hotel | English | 96 (95–96, 3 runs) | 95 (94–96, 3 runs) | 100 |
| Event Hotel | Italian | 97 | 98 | 100 |
| Booking Guide | English | 99 | 99 | 100 |
| Booking Guide | Italian | 100 | 99 | 100 |

Repeated Performance scores are medians with their full ranges. The English Event Hotel tablet has one raw score of 94, with a passing median of 95; it was not re-audited to replace that result. Unannotated scores are single runs according to the runner's automatic repetition rule. Raw JSON/HTML evidence is in `.quality/hotel-guide-second/` (6 reports) and `.quality/hotel-guide-pages/` (16 reports). `git diff --check` passes.

These are local checks. Playwright 1.63.0 uses Chromium 153.0.8010.12, Firefox 155.0 and WebKit 26.6; WebKit is not installed Safari or physical iOS. Lighthouse 13.4.1 uses Chrome 152 and Node 26.7.0, with a custom 768×1024 tablet emulation. Physical devices, live performance, real-user Core Web Vitals and fresh full-site browser/Lighthouse coverage were not measured. Existing `caniuse-lite` and `NO_COLOR` / `FORCE_COLOR` notices remain tooling warnings.

The change is local and has not been pushed or deployed. Preview: http://127.0.0.1:4175/hotel#as-hotel-cambiago.
