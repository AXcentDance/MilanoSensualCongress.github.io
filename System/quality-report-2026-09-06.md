# Website quality and project rules — 6 September 2026

**Local acceptance passed, but CI Lighthouse acceptance failed. Publication
and live verification remain pending.**
All 68 indexable English and Italian pages meet the four 95+ Lighthouse targets
on phone, tablet and desktop in the local run. Including the AS Cambiago
direct-link view in both languages, the indexable-page scope contains 210
page/view/profile combinations and 240 raw reports, with zero local failures.
The user subsequently excluded intentionally non-indexed pages from acceptance;
the runner and this score table now skip them.

| Profile | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- |
| Phone | 96–100 | 95–100 | 100 | 100 |
| Tablet | 95–100 | 95–100 | 100 | 100 |
| Desktop | 100 | 95–100 | 100 | 100 |

The ranges include every indexable page and both hotel views. Performance uses
the documented repeated-run median; the other categories use their lowest
result. Every individual indexable-page run in this final acceptance also scored at least 95 in every category.

Intentionally non-indexed pages are outside the requested quality target.
Their noindex behavior remains unchanged.

[Every page's scores and repeated-run ranges](/Users/slamitza/MilanoSensualCongress/System/quality-scores-2026-09-06.csv)

Browser verification passed 846 cases across Chromium, Firefox and WebKit,
followed by 108 passing checks for the four pages affected by the final hotel
guide addition. Both runs had zero failures, skips or flaky results. Checksums
confirm that all other rendered pages and shared assets were unchanged.
The static gate, 41 Node tests, nine Python tests and workflow validation pass.

The final candidate includes all completed hotel work: AS Cambiago, the two
hotel views, booking copy, stable swipe-image framing, and the matching booking
guide buttons/content in both languages. Its 287 public files match the
tested fixed copy byte-for-byte. The live site has not received these changes.

The separate hotel task subsequently received the instruction to push and
merge. It pushed commit 871d173 and opened
[PR #2](https://github.com/AXcentDance/MilanoSensualCongress.github.io/pull/2).
The first CI run passed the static gate and Chromium, but all three Lighthouse
jobs failed during Chrome startup, before producing scores. Firefox and WebKit
each passed 281 of 282 cases; their remaining reminder-form tests clicked while
the form was still scrolling and sent no request. Those failures remain in
.quality/ci-phone-first.log, .quality/ci-firefox-first/ and
.quality/ci-webkit-first/.

The replacement CI run on commit 1d5595a passed the static gate and all 846
browser cases without failures, skips or flaky results. Chrome startup is
fixed. Its full Lighthouse sweep nevertheless failed:

| CI profile | Performance range | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- |
| Phone | 88–95 | 95–100 | 77 | 100 |
| Tablet | 82–94 | 95–100 | 100 | 100 |
| Desktop | 100 | 95–100 | 77–100 | 100 |

These are medians for Performance and lowest scores for the other categories
across all 68 indexable pages. The AS fragment step did not run after the
default-page command failed, so this CI result is not complete view coverage.
The phone/desktop reports identify Meta's third-party `fr` cookie and the
associated DevTools cookie issue. The slower CI processors also record longer
Meta script tasks. These failures were not present in the local acceptance
and are not being hidden or waived. A user decision is pending on loading Meta
only after visitor consent, which changes tracking coverage. The separate
GitHub Pages setting approval is also still pending.

[Every indexable page's CI scores](/Users/slamitza/MilanoSensualCongress/System/quality-ci-scores-2026-09-06.csv)
and [the completed CI run](https://github.com/AXcentDance/MilanoSensualCongress.github.io/actions/runs/34053732940)
record 610 indexable-page reports, 204 combinations and 203 failures.
Complete raw reports are preserved in the three verified ZIP archives under
.quality/ci-run-34053732940; their expanded duplicates were removed after
archive integrity checks to conserve disk space.

**Agreed scope**

All 68 indexable English and Italian pages must reach at least 95/100 in
Performance, Accessibility, Best Practices, and SEO. Intentionally non-indexed
pages are excluded, following the user's latest scope clarification. The current
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
The completed Linux CI Lighthouse run used Google Chrome 152.0.7977.64.

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
- Every indexable page enters all three Lighthouse profiles. Each category must reach
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

The CI startup fix uses the Google Chrome already installed on the Ubuntu
runner and prints its version. Ubuntu's supported Chrome installation has the
relevant sandbox profile; downloaded developer/test binaries can fail during
startup under its user-namespace restrictions. This is consistent with the
observed connection-refused failure; the replacement CI run verified the correction.
The change keeps the browser sandbox and all Lighthouse audits enabled.
See the [runner image inventory](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)
and [Chromium's Ubuntu sandbox explanation](https://chromium.googlesource.com/chromium/src/+/main/docs/security/apparmor-userns-restrictions.md).

The form-test correction waits for fonts and positions the form before filling
and clicking it. It retains real pointer clicks, the original success/error
assertions, preserved email value and exactly-one-request check. It does not
change form implementation, add test retries or relax assertions.
All 216 repeated form cases pass locally across the three engines and three
viewports; the static gate and all 50 Node/Python regression tests also pass.
Evidence: .quality/browser-reminder-ci-fix-results.json and
.quality/check-ci-fix.log. The compiled Tailwind rebuild is byte-identical,
and all 287 public files remain identical to the accepted snapshot.

The final local release package contains 287 public files. Its HTML and loaded
CSS references resolve inside that package, including clean page URLs, images,
fonts, scripts, styles, favicons, and responsive candidates.

**Verification and evidence**

- Master static gate: all 69 public HTML pages pass; all 50 Node/Python
  regression tests pass. Actionlint 1.7.12 and diff whitespace checks pass.
- Browser suite: 846/846 passed, 18:07–18:12 UTC. Only the four hotel/guide
  HTML files and their generated content changed afterward; 108/108 affected
  browser cases then passed at 18:23–18:24 UTC on the final frozen source.
  The coverage record lists both snapshots and the precise differences.
- All eight rewritten project skills passed validation. The reconciled
  AGENTS.md, six rules and eight skills total 495 lines, versus 1,096 before.
- The final public artifact contains 287 files. Local HTML and loaded CSS
  references resolve inside the package, and the packaged bytes match the
  source and fixed copy used for testing.
- Local Lighthouse: 240 reports for 210 accepted indexable page/view/profile
  combinations. The original 243-report archive is preserved unchanged.
  The normal runner retained its throttling and third-party requests; marginal
  results were repeated using the documented rule. No audits were suppressed.
  The summaries confirm unchanged sources throughout both runs.
  After 139 completed combinations, a Chrome debugging-connection error
  interrupted the runner before its next measurement. The unchanged snapshot
  was resumed with the built-in source/configuration guard; completed reports
  were retained. The interruption remains visible in the audit log.
- Audit timestamps: 2026-09-06T18:24:52.407Z through 2026-09-06T18:53:00.063Z.
  Source SHA-256: a53a63f14ef44a0b0c97531b036c686773113211f3982b717bf1c7ad501a8bc8.
- Visual checks covered representative pages before/after the performance
  fixes, the re-encoded transfer image, both hotel views and guide layouts.
  The hotel task also checked the swipe transition in all three engines at
  375, 661, 768 and 1440px; the photo framing remains stable.

Final evidence:

- [All-page Lighthouse summary](/Users/slamitza/MilanoSensualCongress/.quality/acceptance-frozen-release/summary.json)
- [AS hotel-view Lighthouse summary](/Users/slamitza/MilanoSensualCongress/.quality/acceptance-frozen-as-hotel/summary.json)
- [Complete browser suite](/Users/slamitza/MilanoSensualCongress/.quality/browser-frozen-release-results.json)
- [Final affected-page browser suite](/Users/slamitza/MilanoSensualCongress/.quality/browser-frozen-guide-results.json)
- [Browser evidence coverage](/Users/slamitza/MilanoSensualCongress/.quality/browser-evidence-coverage.json)
- [Static and regression checks](/Users/slamitza/MilanoSensualCongress/.quality/check-final-candidate.log)
- [Final file checksums](/Users/slamitza/MilanoSensualCongress/.quality/frozen-release-complete-manifest.json)
- [CI Lighthouse summary and failures](/Users/slamitza/MilanoSensualCongress/.quality/ci-run-34053732940/acceptance-summary.json)
- [Indexable-only scope regression checks](/Users/slamitza/MilanoSensualCongress/.quality/check-indexable-scope.log)

Representative baseline samples compared with the final acceptance on the
same machine and Chrome version:

| Page/profile | Performance before → after | Accessibility after | Best Practices after | SEO after |
| --- | --- | --- | --- | --- |
| Homepage / phone | 96 → 96 | 100 | 100 | 100 |
| Homepage / tablet | 95 → 96 | 100 | 100 | 100 |
| News / phone | 83 → 98 | 100 | 100 | 100 |
| News / tablet | 95 → 97 | 100 | 100 | 100 |
| Solo guide / phone | 62 → 98 | 100 | 100 | 100 |
| Solo guide / tablet | 92 → 99 | 100 | 100 | 100 |
| Tickets / phone | 95 → 97 | 100 | 100 | 100 |
| Tickets / tablet | 95 → 96 | 100 | 100 | 100 |

The baseline was a sample of eight pages on two profiles, not an original
all-page sweep. The after values come from the final complete acceptance.
Raw baseline reports remain in .quality/baseline.

Earlier failures remain inspectable. The prior 267-report diagnostic sweep
exposed image/preload and integration problems; the 229-report follow-up caught
two intermittent Meta diagnostic-image CSP failures. The shared CSP correction
then passed all 207 pairs in a 233-report sweep before the hotel changes.
Those phases remain in .quality/lighthouse-final, .quality/release-lighthouse
and .quality/acceptance-lighthouse respectively.

The separate hotel-guide task's earlier focused run recorded an English Event
Hotel tablet median of 95, with a 94–96 range. That raw 94 remains in its report
and .quality/hotel-guide-pages; it was not deleted. The final site-wide
acceptance above is a separately identified complete run.

After the hotel work, the English price archive had an isolated tablet median
of 94. Preloading its existing hero image in both languages produced 96/96/96
in each language's focused tablet recheck. Interrupted sweeps in
.quality/acceptance-with-cambiago and .quality/as-hotel-combined-final are marked
incomplete because the source changed. The opening frozen-copy attempt in
.quality/acceptance-frozen-overlap overlapped another task's browser tests and
was stopped. These diagnostic runs were not counted as final acceptance.

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

Intentionally non-indexed pages are excluded from the Lighthouse target.
The remaining baseline tooling warning is Tailwind's outdated caniuse-lite
database message.

Remaining release work:

1. Resolve the Meta tracking decision and the CI Lighthouse failures, then
   verify the final change and update the existing PR #2.
2. Obtain the pending approval to configure GitHub Pages to publish through
   Actions before merging, so direct branch publishing cannot race CI.
   Automatic approval review rejected that setting change because the separate
   "push and merge" instruction did not explicitly authorize a production
   deployment-setting change.
3. After every remote check passes, merge the verified change and let the
   main-branch gates publish its artifact.
4. Use the workflow’s manual live-audit option to check every indexable page against
   the actual domain, recording live results separately from this local evidence.

Publishing is not protected by the prepared workflow until the Pages setting
is activated. The branch and PR exist; no merge or hosting change has been made.
After the update reaches main, existing working branches/worktrees should
incorporate it before future page work, preserving their own uncommitted changes.
