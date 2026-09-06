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
python3 scripts/run_all_checks.py
```

Install `beautifulsoup4` if needed; `requirements-dev.txt` records the supported
checker dependency. Do not maintain hand-edited versions of generated outputs.
CSS-only changes need the critical-CSS workflow and checks, not this entire
content workflow. If an HTML source changed, sitemap freshness can be updated
without inventing an editorial `dateModified`.

Inspect the diff: include all indexable pages, exclude intentional noindex,
reports and tooling, preserve truthful dates and translated canonical URLs.
Confirm new pages in both `llms.txt` and `llms-full.txt` and relevant feeds.
Review inbound links and matching hidden HTML/schema breadcrumbs. Run the local
master gate before publishing generated indexes. Include the regenerated files
in the reviewed change; GitHub Actions does not generate or verify them.
