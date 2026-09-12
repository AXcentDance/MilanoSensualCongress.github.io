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

Inspect the diff: include all indexable pages, exclude intentional noindex,
reports and tooling, preserve truthful dates and translated canonical URLs.
Confirm new pages in both `llms.txt` and `llms-full.txt` and relevant feeds.
Review inbound links and [HTML/schema breadcrumbs](../../rules/breadcrumbs.md).
Include regenerated files in the reviewed change, then follow
[delivery completion](../../rules/delivery.md#verification-and-completion).
