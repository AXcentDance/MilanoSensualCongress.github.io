# Website quality and project rules — 6 September 2026

**Current status: the hotel-guide change is complete; release verification
and publication are pending.** The final hotel and guide changes passed their
scoped static, behavior, browser and Lighthouse checks; see
`System/as-hotel-booking-guide-button-2026-09-06.md` for measured coverage.
The user has requested push and merge of the combined branch. The first frozen
candidate included the two hotel views, updated booking copy and swipe-image
fix; its 287 public files matched the source. Full-site release CI must include
the completed button and guide changes.

All 846 browser cases passed against that frozen candidate, with zero failures,
skips or flaky results, on 6 September 2026, 18:07–18:12 UTC. The static gate,
41 Node tests, nine Python tests and Actionlint also passed. The opening
Lighthouse samples overlapped the separate guide task's browser run and were
stopped. They remain in .quality/acceptance-frozen-overlap as diagnostics.
Final acceptance will include the new guide changes and run in isolation.

The earlier full-site sweep in .quality/acceptance-with-cambiago was stopped
after 213 reports / 178 page-profile pairs because the source files changed.
It also overlapped the hotel browser suite at 16:49–16:55 UTC. The English price
archive's tablet median was 94; its subsequent isolated recheck was also 94.
Preloading the same hero image in both languages resolved the measured failure:
English and Italian tablet repeats each scored 96/96/96. Their image, layout,
text and metadata were preserved. All interrupted reports remain diagnostics,
not final acceptance evidence.

**Earlier accepted version (before the hotel changes).** All 68 indexable
English and Italian pages passed all four categories on phone, tablet, and
desktop. The final sweep produced 233 reports covering all 207 page/profile
pairs, including the intentional 404. Every individual normal-page result was
at least 95; no averaging was needed to rescue a failing run. The final browser
suite passed all 774 cases against the same rendered files, with zero failures,
skips, or flaky results.

| Profile | Performance range | Accessibility range | Best Practices | SEO |
| --- | --- | --- | --- | --- |
| Phone | 96–100 | 95–100 | 100 | 100 |
| Tablet | 95–100 | 95–100 | 100 | 100 |
| Desktop | 100 | 95–100 | 100 | 100 |

These ranges cover the 68 indexable pages. The 404 keeps noindex: its raw SEO
score is 63, with Performance 99/99/100 and Accessibility/Best Practices 100.

[Every page’s scores and repeated-run ranges](/Users/slamitza/MilanoSensualCongress/System/quality-scores-2026-09-06.csv)

The live site has not received these changes. Upload, review, and gated
publication await the user’s explicit approval after automatic approval review
rejected the upload/PR operation. The original main branch remains unchanged.

**Agreed scope**

All 68 indexable English and Italian pages must reach at least 95/100 in
Performance, Accessibility, Best Practices, and SEO. Lighthouse also checks the
intentional 404 page, with its noindex SEO result shown separately. The current
appearance is preserved, with small responsive and accessibility fixes.
The user approved preserving tracking and allowing its two verified gateway
origins, and publishing future releases only after the quality checks pass.

Lighthouse runs in Chrome with three profiles: its standard phone profile, a
custom 768×1024 tablet profile using mobile throttling, and desktop at 1440×900.
Browser behavior is checked separately in Chromium, Firefox, and WebKit at
375×812, 768×1024, and 1440×900. The local tools are Lighthouse 13.4.1 with
Chrome 152.0.7977.76, and Playwright 1.63.0 with Chromium 153.0.8010.12,
Firefox 155, and WebKit 26.6. Firefox uses touch-enabled viewport checks;
Playwright does not offer Firefox’s mobile emulation flag.

**What changed on the site**

| Problem | Smallest implemented fix |
| --- | --- |
| Desktop navigation squeezed the logo and pushed Contact/language links off tablet screens | Use the mobile menu until 1280px, prevent logo shrinkage, and provide 44px menu controls |
| Two article menus referenced a missing element | Restore the English and Italian David y Ines mobile menus |
| Terms pages lacked language switches | Add English/Italian links to both menus |
| News links depended on color alone | Underline paragraph links and add visible keyboard focus |
| Contact-page decoration exceeded the phone width | Bound the existing decorative glow to the available width |
| Solo guide started a large WebGL library and blocked the main thread | Recreate the constellation in Canvas 2D; cap animation at 30fps and pause it offscreen/in hidden tabs |
| Homepage video ignored reduced-motion/data-saving preferences | Keep the existing poster and skip autoplay for those preferences; retain normal autoplay |
| Artists-page text lost contrast during its pulse animation | Keep that text at its normal opacity |
| Artists-page CSS requested a blocked external world-map image | Remove the unused request; it was already invisible under the existing CSP |
| Meta Pixel gateways, POST fallback, and occasional diagnostic images were blocked by CSP | Allow the two verified gateway origins, the existing Facebook /tr/ transport, and diagnostic images from the existing Meta script domain |
| Transfer hero was a large JPEG with a misleading .webp extension | Convert it to real WebP at the same 1024×1024 dimensions: 868 KiB → 133 KiB; load it eagerly |
| Italy guide used a 346 KiB background where an existing 88 KiB variant was available | Use and preload the bounded variant in both languages |
| Archived Full Pass article missed the tablet performance target in repeated measurements | Preload its existing hero image in both languages |
| Five pages lacked an explicit favicon; many icons advertised the wrong image type | Reuse the existing logo and declare its actual WebP type |
| One English article pointed hreflang at the wrong Italian article | Correct the Klau y Ros alternate URL |
| Two article graphs referenced an undefined WebSite | Add the missing WebSite definitions |
| Italian homepage sitemap URL lacked its canonical slash | Generate /it/ consistently |

The performance fixes preserve existing prices, event dates, ticket
destinations, form endpoints and Pixel ID/events. Separate user-requested hotel
work adds AS Cambiago, its supplied rates and booking destination, a bilingual
hotel selector and the corresponding booking guide. Its comparison with public
hotel rates is organizer-supplied copy, not an independently verified rate
comparison. The new code retains self-hosted Inter, Playfair Display,
Tailwind 3.4.17, the Font Awesome subset, existing photos, and the navy/pink/purple
visual identity.

The approved tracking origins were verified against the public configuration
for Pixel 2083020305980459. Its OpenBridge configuration names the AWS endpoint
and the Google Cloud fallback below:

- [Verified AWS gateway](https://dv-c3e594c6d429469e90b54478358619c3.ecs.us-east-1.on.aws)
- [Verified Google Cloud fallback](https://bded8a3c6ae-1-1053047382554.us-central1.run.app)

The observed Pixel fallback POST to its existing Facebook /tr/ endpoint is
allowed specifically under form-action. The existing script/connect domain
connect.facebook.net is also allowed under img-src: the full sweep observed
Meta’s occasional OpenBridge diagnostic image request there. No wildcard host
allowance was introduced. These transports are checked by the static gate, so
a copied page cannot silently omit them.

No real leads, bookings, or form messages were submitted during testing.
Functional tests simulate the form responses; Lighthouse loads third parties
normally and does not hide their errors or processing cost.

**Instruction conflicts resolved**

The original AGENTS.md and .agent instructions contained 1,096 lines. The
reconciled set contains 495 lines, a reduction of approximately 55%.
The audit covered all seven original rule files, all eight project skills,
AGENTS.md, the preview configuration, and the verification/deployment workflow. Local Claude settings contain only
permissions. Two older Claude worktrees contain historical copies of the
project; their separate branches were preserved. They must incorporate the
updated main branch before being used for future website work.

| Conflicting or stale instructions | Canonical replacement |
| --- | --- |
| Generic instructions for AXcent/Zurich/German mixed into a Milan English/Italian project | delivery.md defines this site, its two languages, actual translated URLs, and visitor purpose |
| Tailwind 4, Shadcn, Framer Motion, and generic stack suggestions conflicted with the static self-hosted site | Keep plain HTML/CSS/JS, compiled Tailwind 3.4.17, existing fonts/icons, and small shared scripts |
| Suggestions to avoid Inter or vary colors/fonts conflicted with homepage brand coherence | The homepage brand rule takes precedence; frontend-design is the single design workflow |
| Mandatory motion and opacity introductions conflicted with visible first paint and accessibility | Keep primary content visible initially; use optional restrained motion with reduced-motion support |
| Rigid keyword counts, density, word counts, and invented SEO scoring encouraged unnecessary rewrites | Use visitor intent, truthful content, actual evidence, and Lighthouse's named categories |
| Visible editorial bylines/dates conflicted with the metadata-only article rule | Preserve accurate authors/dates in head metadata and JSON-LD only |
| Frozen example prices and performer profiles could contradict the current site | Read current event facts, the price checker, and the actual artist pages |
| Two index synchronization skills maintained competing workflows | sync-indexes is canonical; site_metadata_sync is a short compatibility alias |
| Two design skills maintained competing instructions | frontend-design is canonical; ui-ux-designer is a short compatibility alias |
| “Every font must be preloaded” could create unnecessary competing downloads | Preload the font faces actually used above the fold |
| Fixed page-folder lists could omit future nested pages or accidentally include reports | Share one recursive public-page inventory across the gates, Tailwind, and image application |
| The old image checker rejected decorative empty alt text | Accept valid decorative semantics and distinguish missing alt from intentionally empty alt |
| Filenames alone were treated as proof of image encoding | Check actual WebP signatures and image-file existence |
| Hreflang links could allow an isolated translated pair to pass the orphan check | Require a real HTML-link path from a homepage |
| The image application script mishandled nested Italian paths and explicit hero priority | Resolve paths from the actual page location and preserve eager LCP loading |

The obsolete rules.md, objective.md, and it.md were consolidated into
delivery.md. The original article-metadata-only, breadcrumb, and homepage-brand
rules remain authoritative. performance.md now defines the measurable target,
loading defaults, browser coverage, and reporting limits.

**What prevents future regressions**

- The master gate checks all public HTML automatically, including new nested
  pages. It validates metadata, schema, canonical/hreflang relationships,
  sitemap coverage, headings, image dimensions/alt/encoding, hidden breadcrumbs,
  required shared loaders, verified tracking transports, favicons, menu targets,
  and asset-version consistency.
- The hreflang checker now compares the actual reciprocal URLs. Previously, an
  English link's mere presence could allow a wrong destination to pass.
- Checker exit codes and warnings are respected. A success-looking message
  can no longer hide a failing process.
- Tailwind builds use the same page inventory, excluding generated inline CSS
  and report directories. CI checks that committed CSS matches current classes.
- Critical CSS is regenerated from its source files and checked by content,
  including the shared accessibility defaults.
- Every page enters all three Lighthouse profiles. Each category must reach
  95; marginal or failing results are repeated three times. Performance uses
  the median and retains the whole range; the other categories use their
  lowest result, so intermittent defects cannot be averaged into a pass.
  A run also fails if its source files change while it is running.
- The release workflow also audits the AS Cambiago direct-link view in both
  languages on all three profiles, in addition to the default Devero view.
- Targeted audit lists reject unknown page names instead of silently omitting
  a mistyped language counterpart. A regression test protects this behavior.
- Tailwind builds only require a shared cache-version bump when the compiled
  CSS bytes change. Existing utilities can be reused without changing every
  page's cache key; critical CSS is still regenerated and checked.
- The browser suite checks every page in nine engine/viewport combinations,
  plus form outcomes, native controls, missing URLs, reduced motion, and
  representative pages without JavaScript.
- Release files contain public content/assets only. Agent instructions,
  tooling, dependencies, and reports are excluded from the deployed artifact.
  The packager checks local HTML and loaded CSS references against the actual
  package, rejecting resources omitted from the public file list. A regression
  test covers a download present in the checkout but absent from the release.

These checks make future pages subject to the same acceptance criteria.
New content still needs truthful facts, translation review, visual inspection,
and fixes if its measurements fail.

**Publishing**

The previous GitHub Pages configuration published directly from unprotected
main, independently of the quality workflow. The prepared replacement deploys
the public artifact only after static checks, all browser jobs, and all
Lighthouse jobs pass. Index generation happens inside the artifact, eliminating
the old follow-up bot commits; IndexNow is notified after successful deployment.

GitHub Pages must use GitHub Actions as its publishing source for this to take
effect. The workflow uses GitHub's artifact deployment and job dependencies.
See [GitHub's custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

The artifact preserves .well-known/security.txt and .nojekyll. Actionlint
1.7.12 validates the workflow. A manual live-audit option runs the three
Lighthouse profiles on separate CI machines against the published site, without
entering the deployment job. This allows live verification to finish faster.

The final local release package contains 280 public files. Its HTML and loaded
CSS references resolve inside that package, including clean page URLs, images,
fonts, scripts, styles, favicons, and responsive candidates.

**Verification**

- Master static gate: passed across 69 HTML pages.
- Existing behavior tests plus new quality-result tests: 40 passed.
- Python quality-gate regression tests: nine passed.
- Final browser suite: 774 passed, zero skipped/flaky/failed, in 187 seconds.
  It ran 6 September 2026, 14:58–15:01 UTC. Earlier focused and complete runs
  remain in .quality for comparison.
- All eight rewritten project skills passed skill validation.
- Before/after visual comparison: solo guide at phone/tablet/desktop; additional
  inspection of Italian homepage, tickets, news, levels guide, and terms.
  The transfer image before/after comparison preserves the same composition
  and layout after the 85% size reduction.
- Complete diagnostic Lighthouse sweep: 267 reports covering all 207
  page/profile pairs. It exposed the final tracking, preload, and image defects.
- Targeted verification of those fixes: four tablet cases passed; contact
  99/100/100/100, Italy guide 97/100/100/100, party article 100/100/100/100,
  transfer 97/100/100/100.
- Subsequent complete sweep: 229 reports for 207 pairs; 205 passed. The two
  failures were Best Practices 92 from the same occasional Meta diagnostic
  image blocked by CSP. Normal-page Performance was 96–100 on phone/tablet
  and 100 on desktop; Accessibility 95–100 and SEO 100 throughout.
- Final acceptance sweep after that shared CSP correction: 233 reports, all
  207 page/profile pairs passed. It ran 6 September 2026, 14:31–14:57 UTC.
  The runner confirmed that rendered sources were unchanged throughout.
  Source fingerprint: e253c80e067fb8562305f6203034ed2d9013fe9753aac7917d0736e1acc7c246.
- Final static gate, nine Python tests, 40 Node tests, Actionlint, and diff
  whitespace checks passed. All 280 packaged files match their source bytes.

Detailed final evidence:

- [Lighthouse summary](/Users/slamitza/MilanoSensualCongress/.quality/acceptance-lighthouse/summary.json)
- [Browser results](/Users/slamitza/MilanoSensualCongress/.quality/browser-acceptance-results.json)
- [Static and regression checks](/Users/slamitza/MilanoSensualCongress/.quality/check-acceptance.log)

Representative initial baseline samples compared with final acceptance on the
same machine and Chrome version:

| Page/profile | Performance before → after | Accessibility after | Best Practices after | SEO after |
| --- | --- | --- | --- | --- |
| Homepage / phone | 96 → 96 | 100 | 100 | 100 |
| Homepage / tablet | 95 → 95 | 100 | 100 | 100 |
| News / phone | 83 → 98 | 100 | 100 | 100 |
| News / tablet | 95 → 97 | 100 | 100 | 100 |
| Solo guide / phone | 62 → 98 | 100 | 100 | 100 |
| Solo guide / tablet | 92 → 99 | 100 | 100 | 100 |
| Tickets / phone | 95 → 97 | 100 | 100 | 100 |
| Tickets / tablet | 95 → 96 | 100 | 100 | 100 |

The baseline was a representative sample, not an original all-page sweep.
Final values above come from the complete acceptance run. Raw baseline and
earlier recheck reports remain in .quality/baseline and
.quality/after-shared-fixes. An interrupted sweep in .quality/lighthouse-complete
also remains available: it exposed the artists defects and was affected by a
confirmed orphaned audit browser consuming a CPU core. That process was stopped
before the diagnostic all-page sweep; no results were silently deleted.
That complete diagnostic sweep is retained in .quality/lighthouse-final; the
229-report follow-up is retained in .quality/release-lighthouse. The final
acceptance reports are in .quality/acceptance-lighthouse. Each phase is kept
separately so earlier failures remain inspectable.

**Where the current rules live**

- [AGENTS.md](/Users/slamitza/MilanoSensualCongress/AGENTS.md) routes each task.
- [Delivery rule](/Users/slamitza/MilanoSensualCongress/.agent/rules/delivery.md)
  defines the bilingual editing and verification workflow.
- [Quality rule](/Users/slamitza/MilanoSensualCongress/.agent/rules/performance.md)
  defines the 95+ target and rendering defaults.
- [Publishing workflow](/Users/slamitza/MilanoSensualCongress/.github/workflows/site-checks.yml)
  enforces the gates before deployment once activated.

**How to maintain this**

For a fresh checkout, install Node 22.19+ and Chrome, then run:

    npm ci
    python3 -m pip install -r requirements-dev.txt
    npx playwright install --with-deps chromium firefox webkit

For a page change, follow AGENTS.md's skill routing, update both languages,
rebuild/version changed assets, and run the relevant generators once. Then:

    npm run check
    npm run test:browser
    npm run audit:lighthouse
    npm run audit:lighthouse -- --pages=hotel.html,it/hotel.html --fragment=as-hotel-cambiago --output=.quality/lighthouse-as-hotel

The Lighthouse runner supports selecting pages/profiles for diagnosis and
resuming an interrupted run only when sources and configuration are unchanged.
Local detailed output lives in .quality; CI retains quality artifacts for 14 days.

**Measurement limits and remaining work**

Scores are lab results from the local compressed preview, not measurements of
the public deployment. Lighthouse uses Chrome; its tablet profile is not a
physical iPad. Playwright WebKit is not installed Safari or physical iOS.
Real devices, field Core Web Vitals, Search Console, rankings, and live payment
completion are outside this measured evidence.

The intentional noindex 404 has a raw Lighthouse SEO score of 63; its other
categories are still subject to the target. The remaining baseline tooling
warning is Tailwind's outdated caniuse-lite database message.

Remaining actions requiring the pending remote authorization:

1. Upload the reviewed branch to AXcentDance/MilanoSensualCongress.github.io
   and open the prepared draft pull request.
2. Run and inspect the remote quality checks. Configure GitHub Pages to publish
   through Actions before merging, so direct branch publishing cannot race CI.
3. Merge the verified change and let the main-branch gates publish its artifact.
4. Use the workflow’s manual live-audit option to check every public page against
   the actual domain, recording live results separately from this local evidence.

Publishing is not protected by the prepared workflow until the Pages setting
is activated. No push, pull request, merge, or hosting change has been made.
After the update reaches main, existing working branches/worktrees should
incorporate it before future page work, preserving their own uncommitted changes.
