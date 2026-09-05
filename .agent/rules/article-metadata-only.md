---
trigger: always_on
---

# Article authorship and dates belong only in metadata

- On every article page, including news articles, blog posts, and guides, keep the article author, first-publication date, and last-updated date exclusively in the page's `<head>` metadata and unified JSON-LD graph.
- Do not add author bylines, publication dates, update notices, or equivalent labels to the article header, body, or footer. Do not move them into hidden body elements, tooltips, or HTML comments as a workaround.
- This applies equally to English and Italian pages. For example, do not display “By Milano Sensual Congress”, “Updated September 5, 2026 · First published May 8, 2026”, “Di Milano Sensual Congress”, “Aggiornato il”, or “Pubblicato il”.
- Preserve accurate `author`, `datePublished`, and `dateModified` properties in the article's `BlogPosting` or `Article` JSON-LD entity, plus any corresponding head metadata. Keep the original publication date when an article is updated.
- Event dates, workshop schedules, ticket deadlines, and other dates that are part of the article's subject matter may remain visible. This rule concerns the article's own authorship and editorial timestamps.
- Apply this rule when creating or editing article pages. It takes precedence over any skill or template suggesting a visible byline or publication/update date.
