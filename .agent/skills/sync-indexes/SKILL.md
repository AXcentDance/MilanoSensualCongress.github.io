---
name: sync-indexes
description: Regenerate the sitemap, AI context, Markdown twins and feeds after page, metadata or substantive content changes; the single index workflow for this site.
---

# Synchronize derived files

Run once after completing bilingual page additions/removals/renames, metadata
changes, or substantive content edits, from the repository root:

```bash
python3 scripts/sync_social_meta.py
python3 scripts/generate_md_twins.py
python3 scripts/generate_rss.py
python3 scripts/generate_sitemap.py
python3 scripts/generate_llms_text.py
```

Install `beautifulsoup4` if needed; `requirements-dev.txt` records the supported
checker dependency. Do not maintain hand-edited versions of generated outputs.
If a generator fails, resolve its reported error and rerun it before proceeding
with dependent generation or publication. Preserved older outputs do not count
as a successful update; optional omissions such as a page without images are valid.
CSS-only changes use the performance rule's
[build and critical-CSS workflow](../../rules/performance.md#render-and-load).
If an HTML source changed, sitemap freshness can be updated while preserving
the [editorial date policy](../../rules/article-metadata-only.md).

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
