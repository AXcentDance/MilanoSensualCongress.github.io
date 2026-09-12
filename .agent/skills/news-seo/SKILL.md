---
name: news-seo
description: Create or update bilingual congress news, articles, and guides with truthful metadata, useful internal links, and the site's established visual style.
---

# News and articles

Read the project rules plus [design](../frontend-design/SKILL.md) and
[schema](../schema-graph/SKILL.md) for a new article.
Choose a clear visitor question and answer it accurately in natural language.
Use a descriptive unique title, one H1, an honest meta description, and logical
headings. Mention Bachata/event/location context when relevant; no keyword or
word-count quotas.

Create/update the English article in `news/` and its Italian counterpart in
`it/news/`. Pair their actual slugs with reciprocal hreflang links. When adding
an article, link it from both news indexes and relevant existing pages; add
contextual links to tickets, artists, hotel, or transport where useful.

Follow the [article metadata rule](../../rules/article-metadata-only.md) for
authorship, date placement, and when editorial dates may change.

Use one head JSON-LD graph with `BlogPosting`/`Article` as the article's primary
entity. Include the congress entity when the article discusses it, using current
facts from the sources in the schema skill. Do not relabel the global event's
primary page as every article. Use the `Home > News > Article` hierarchy;
implement its HTML trail and schema according to the
[breadcrumb rule](../../rules/breadcrumbs.md).

Use relevant images following the [image](../../rules/image-seo.md) and
[performance](../../rules/performance.md) rules. Finish with
[sync-indexes](../sync-indexes/SKILL.md), then
[delivery completion](../../rules/delivery.md#verification-and-completion).
