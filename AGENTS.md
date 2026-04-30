# Agent Instructions

These instructions are mandatory for any AI agent working in this repository.

## First Step

Before answering with a plan or making any code, content, SEO, design, form, image, metadata, or structural change:

1. Inspect `.agent/rules/`.
2. Inspect `.agent/skills/`.
3. Apply every relevant rule and skill to the current task.

Do not treat `.agent` files as optional references. They are the canonical project instructions for this website.

## Always-On Project Rules

- Apply website changes equivalently to both the English and Italian versions whenever a matching page or flow exists.
- Act as a senior SEO expert and web designer for a bachata congress website.
- Prioritize Google discoverability, AI crawler clarity, international audience reach, and conversion to ticket buyers.
- When adding a new page or significantly changing metadata/content, regenerate:
  - `sitemap.xml`
  - `llms.txt`
  - `llms-full.txt`
- For questions or requests that need planning, present the implementation plan first and ask before changing files, unless the user has already explicitly asked to make the change.

## Required Skill Checks

Use the relevant `.agent/skills/*/SKILL.md` instructions before working:

- `news-seo`: required for news articles, blog posts, timeline updates, and article SEO.
- `sync-indexes` and `site_metadata_sync`: required after adding pages or changing important metadata/content.
- `schema-graph`: required for schema, metadata, SEO page work, and new pages.
- `frontend-design` or `ui-ux-designer`: required for visual/layout/interface changes.
- `audit`: required for SEO audits or site health analysis.
- `find-keywords`: required for keyword research or targeting strategy.

## Verification Expectations

After relevant changes, run the project checks that match the work, such as:

```bash
python3 scripts/check_html_syntax.py
python3 scripts/audit_links.py
python3 scripts/audit_schema.py
python3 scripts/audit_hreflang.py
python3 -c "import xml.etree.ElementTree as ET; ET.parse('sitemap.xml')"
```

Report any checks that could not be run, and do not hide pre-existing failures.
