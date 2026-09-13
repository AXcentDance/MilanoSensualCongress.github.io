---
name: sync-indexes
description: Regenerate the sitemap, AI context, Markdown twins and feeds after page, metadata or substantive content changes; the single index workflow for this site.
---

# Synchronize derived files

Run once after completing bilingual page additions/removals/renames, metadata
changes, or substantive content edits, from the repository root:

```bash
npm run sync:indexes
```

[`scripts/sync_indexes.py`](../../../scripts/sync_indexes.py) owns the order:
validate shared facts, synchronize social metadata, then produce Markdown twins,
feeds, sitemap and LLM exports. It stops at the first failure. Earlier completed
steps may already have updated files; resolve the error, rerun the workflow and
review the complete diff before publication. Preserved older outputs do not
count as a successful update. Optional omissions such as a page without images
are valid. Install declared Python dependencies from `requirements-dev.txt`;
social-image generation also uses the image tools in the performance workflow.
Do not maintain hand-edited versions of generated outputs.
CSS-only changes use the performance rule's
[build and critical-CSS workflow](../../rules/performance.md#render-and-load).

Sitemap `lastmod` follows the content revision recorded in
[`scripts/page_revisions.json`](../../../scripts/page_revisions.json).
Existing verified dates were imported from Git history. Synchronization records
each new substantive source revision once; unchanged content, formatting and
commits retain that date. It is the source-revision date, not a claim that the
change is already deployed. Main content/media, headings, image backgrounds,
labelled links, search metadata and structured facts count; CSS colors/classes,
scripts and asset cache versions alone do not. The sitemap and its revision
record are written together. Include both in the same reviewed release; no
preliminary content commit is needed. Keep the revision record in Git and restore
it if missing instead of resetting old dates. Future dates fail verification.
The [editorial date policy](../../rules/article-metadata-only.md) independently
owns article publication/update dates; synchronization never rewrites those.
Image identity follows the [image source naming policy](../../rules/image-seo.md).
Background-image declarations in a shared stylesheet are treated conservatively
as relevant to its referencing pages, including responsive or interactive states;
the revision reader does not pretend to evaluate every browser state.

The master gate compares Markdown, RSS, sitemap (including dates, images and
language links) and LLM exports with their generators' current rendering using
read-only checks. A partial synchronization cannot pass as complete. Run the
whole sync again after resolving a failed step.

RSS selects the page's Article/BlogPosting/NewsArticle metadata structurally.
Missing, invalid or conflicting required article metadata stops both feeds;
legitimate non-article pages are omitted. Date-only publication values serialize
at midnight UTC without changing the source date; timed values require offsets.
LLM exports contain no rebuild timestamp: unchanged source produces unchanged
public content. Explicit/prebuilt social JPG cards remain authoritative; newly
generated cards record their source in `images/og/generated-cards.json` so future
source changes refresh the right derivative without replacing authored cards.

Public-page discovery and indexing decisions belong to
[`scripts/site_files.py`](../../../scripts/site_files.py). Its directory exclusions
and explicit utility-page registry are shared by generators and checks. A new
nonindexed utility page needs both a justified registry entry and a robots
`noindex` directive in its head; do not add ordinary content or sales pages to
silence a failure. Utility HTML remains public and receives functional checks,
but is excluded from sitemap, Markdown/LLM exports, feeds and IndexNow selection.
`noindex` is not a privacy protection; private material must stay outside public
and publishable files.

Inspect the diff: include all indexable pages, apply that shared policy,
preserve truthful dates and translated canonical URLs.
Confirm new indexable pages in both `llms.txt` and `llms-full.txt` and relevant feeds.
Review inbound links and [HTML/schema breadcrumbs](../../rules/breadcrumbs.md).
Include regenerated files in the reviewed change, then follow
[delivery completion](../../rules/delivery.md#verification-and-completion).
