---
name: schema-graph
description: Maintain accurate page metadata and a connected head JSON-LD graph for this bilingual site, including new pages and SEO fixes.
---

# Metadata and schema

Use one `<script type="application/ld+json">` in the head of each indexable
page, with `@context: https://schema.org` and a top-level `@graph`. Include only
entities that describe the page and verified event facts; more markup is not
automatically better. Do not promise rich results from valid JSON alone.

Reuse the global IDs `https://milanosensualcongress.com/#organization`,
`https://milanosensualcongress.com/#website`, and
`https://milanosensualcongress.com/#event`. Give the local WebPage its canonical
URL plus `#webpage`; connect it to the WebSite and its `#breadcrumb`. Keep
subpage HTML/schema hierarchy consistent with the breadcrumb rule. A homepage
may retain its existing one-item schema trail.

Select a primary entity that matches the page: Article/BlogPosting for an
article, ContactPage for contact, and the congress DanceEvent on its main event
page. A related congress entity in an article is not itself that article.
FAQ markup must match real questions and answers that visitors can access.

## Current facts, not frozen templates

- Read `index.html` and `it/index.html` for current organization/event facts.
- Read `scripts/update_price.py` for the canonical current Full Pass price and
  deadline. Use its `--check` gate. A price update must also reconcile visible
  tickets/copy/countdowns; the script does not update every visible price.
- Read `artists.html` and `it/artists.html` for the current lineup. Reuse verified
  official profile URLs when available; do not invent social handles or require
  a fixed number of performers.
- A complete event uses actual name, timezone-aware start/end, status, attendance
  mode, venue/address, image, description, organizer, and current ticket offers.
  Keep timezone offsets on timed deadlines. Preserve historical article dates.
- Do not copy stale example prices, year-specific offers, or unverified facts
  into new pages. Do not add unsupported ratings or irrelevant schema types.

Use one canonical URL, reciprocal `en`/`it`/`x-default`, language-correct titles,
descriptions and `inLanguage`. Apply equivalent graph changes to both languages.
Run `sync_social_meta.py` after title/description changes, follow `sync-indexes`
for generated files, and run the master gate. Its schema checks validate local
invariants, not search-engine eligibility; inspect warnings and verify official
search documentation when making eligibility claims.
