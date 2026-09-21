---
trigger: always_on
---

# Delivery workflow

Follow the congress-only positioning and European/worldwide audience scope in
[AGENTS.md](../../AGENTS.md#precedence-and-scope). Help international Bachata
dancers discover Milano Sensual Congress, understand the event, and buy tickets.
Use accurate, useful content and accessible, fast pages. Do not promise rankings,
clicks, rich results, or AI-crawler inclusion.

Apply equivalent site changes to English and Italian. Use the actual reciprocal
`hreflang` URLs to find translated counterparts; translated slugs often differ.
The English root and `/it/` are the two supported languages. Preserve established
URLs and event facts; obtain facts from the current site and verified sources.

Use static HTML, the existing self-hosted assets, and small shared scripts.
Do not add a framework, font family, icon library, or animation dependency to
solve a problem that the current stack handles simply.

For a new page, start from the closest current page and follow the
[design](../skills/frontend-design/SKILL.md) and
[schema](../skills/schema-graph/SKILL.md) workflows.
Include a useful internal link from an existing page and the translated partner.
The static gate and page-discovery tools find new HTML pages automatically; copied markup still
needs inspection and testing.
[`scripts/site_files.py`](../../scripts/site_files.py) owns public-page discovery
and the approved nonindexed utility-page policy; use it for page selection
instead of maintaining another exclusion list or robots parser.

For page additions, removals, renames, metadata or substantive content changes,
follow [sync-indexes](../skills/sync-indexes/SKILL.md) once after the edits; it
owns social metadata, sitemap, feeds, and LLM/Markdown outputs. For asset builds,
follow [performance](performance.md#render-and-load). Editorial dates follow
[article metadata](article-metadata-only.md); CSS-only work needs no content rewrite.

## Verification and completion

Private `.agent/context/` notes and `output/` drafts stay ignored and outside
the Git index. The master gate verifies these exclusions. Before a requested
commit, review new files explicitly and run
`python3 scripts/check_release_files.py --staged` after staging the intended
files; this catches omitted new helpers as well as accidentally included private
paths. The command only reads Git and never stages, commits or publishes.
Its staged mode also rejects tracked changes omitted from the selection,
including unstaged exclusion rules; ignored Finder metadata is left alone.

Choose checks for the complete change set. Before a release, consider all files
being released, not only the latest task.

While editing, run the checker or regression tests that cover the affected
behavior. The [performance rule](performance.md#measured-acceptance) owns the
scope of rendered checks: affected pages and views, including their shared
dependencies and translations. Its selectors support both quick diagnosis and
the final required coverage; retain its browser, device and score requirements.

An internal-instructions or memory-only change set may contain only:

- The root `AGENTS.md`.
- Markdown rules directly in `.agent/rules/`.
- `.agent/skills/*/SKILL.md` instruction files.
- Markdown notes under `.agent/context/`, including its archives.

For this case, review the diff, verify affected file references and heading
anchors (and skill frontmatter if edited), check consistency with current
instructions and preserved protections, and confirm that no private information
is being introduced into public or publishable files. Report these documentation
checks. Do not run website generators, the static site gate, form/analytics tests,
browser tests, or Lighthouse solely for these internal edits.

Public Markdown page twins, site content/assets, scripts, tests, configuration,
and dependencies are outside this exception. If the change set includes any
file outside the list, or its classification is uncertain, use the normal gates
below. Explicitly requested checks still apply.

For all other change sets, after the necessary generators, run locally:

```bash
npm run check
```

This is the maintained entry point for the static site gate, Python generator
and checker regression tests, and protected Node form/analytics tests. Its
implementation belongs to `package.json`; do not maintain a second command list.

For rendered site changes, also run the affected-page browser and Lighthouse
checks defined in [performance](performance.md#measured-acceptance). The fast
static gate remains site-wide to catch broken cross-page relationships such as
canonical/hreflang, schema and generated-index consistency. A skill's reference
to this workflow does not require another identical passing run on unchanged
files. Audit baselines and checks after further changes still apply.
Fix causes instead of weakening checks. Preserve verification results and report
measured coverage, failures, warnings, and anything not tested; distinguish pre-existing issues from
regressions. A static pass alone never proves a Lighthouse score.

Preserve user work. Do not change prices, dates, ticket destinations, form
endpoints, or tracking behavior incidentally.

## Publication

Leave changes local: push only when explicitly requested for those changes.
Earlier push approval does not authorize subsequent edits. Publishing and external
account changes require authorization within the conversation.

GitHub Pages publishes from the root of the `main` branch. Complete the local
verification above before a release. Include regenerated indexes with the
corresponding content change; no CI job regenerates or commits them. The user removed GitHub Actions
quality automation, so do not recreate it or require an Actions-based publishing
source unless the user requests that change. GitHub's own Pages build/deployment
process remains separate from project quality checks.

### IndexNow after publication

The notification-only [IndexNow workflow](../../.github/workflows/indexnow.yml)
listens for successful `pages build and deployment` runs on `main`. It does not
build, regenerate, commit or deploy the site, and does not restore CI quality
checks. Its read-only GitHub token verifies the published commit and finds the
previous successful Pages build, so failed builds do not become the comparison
baseline. It reuses the public IndexNow ownership file already served at the
site root; no additional secret is required.

[`scripts/ping_indexnow.py`](../../scripts/ping_indexnow.py) submits added,
changed, renamed and removed canonical page URLs. Current-page selection uses
the shared page policy; the previous published sitemap supplies removed URLs.
Revision fingerprints include substantive shared-content changes. Markdown,
LLM exports, utility pages and private files are not submitted as new pages.
The script verifies the live ownership file before submission and retries
temporary network/service failures. A received notification is not proof of
indexing or AI citations.

Inspect `Notify IndexNow` in GitHub Actions after a release. Rerun a failed job
to retry that release's exact range, even if a later release is already live.
Alternatively, `Run workflow` on `main` resends all current indexable pages and
the latest release's removed URLs; it requires that `main` has finished
publishing. A read-only local preview of a release range is:

```bash
python3 scripts/ping_indexnow.py --before <previous-published-commit> --dry-run
```

Activation requires publishing the workflow to `main` under the explicit-push
rule above. Local verification must mock IndexNow submissions; it must not send
notifications for unpublished changes.
