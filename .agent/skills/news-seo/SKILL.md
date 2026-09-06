---
name: news-seo
description: Create or update bilingual congress news, articles, and guides with truthful metadata, useful internal links, and the site's established visual style.
---

# News and articles

Read the project rules plus the design and schema skills for a new article.
Choose a clear visitor question and answer it accurately in natural language.
Use a descriptive unique title, one H1, an honest meta description, and logical
headings. Mention Bachata/event/location context when relevant; no keyword or
word-count quotas.

Create/update the English article in `news/` and its Italian counterpart in
`it/news/`. Pair their actual slugs with reciprocal hreflang links. When adding
an article, link it from both news indexes and relevant existing pages; add
contextual links to tickets, artists, hotel, or transport where useful.

Keep article author, publication and modification dates exclusively in head
metadata and JSON-LD, following `.agent/rules/article-metadata-only.md`.
Preserve original publication dates. Update modification dates truthfully for
substantive editorial changes; CSS/build changes do not reset them.

Use one head JSON-LD graph with `BlogPosting`/`Article` as the article's primary
entity. Include the congress entity when the article discusses it, using current
facts from the sources in the schema skill. Do not relabel the global event's
primary page as every article. Keep hidden `Home > News > Article` HTML
breadcrumbs and matching schema per the breadcrumb rule.

Use relevant, accurately described images; follow the image/performance rules.
Finish with the canonical `sync-indexes` workflow and required gates.
