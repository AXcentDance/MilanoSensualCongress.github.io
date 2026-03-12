---
name: Sync Site Indexes & AI Context
description: Updates both the search engine sitemap and the llms-full.txt context file to ensure all changes are indexed and accessible to AI agents.
---

# Sync Site Indexes & AI Context

Use this skill whenever you add a new page, rename a file, or make significant content changes to existing pages. This ensures that both search engines and AI agents have the most recent version of the site.

## 1. Run Synchronization Scripts
Execute the following commands in the project root:

```bash
# Update Sitemap (for Google/Bing)
python3 scripts/generate_sitemap.py

# Update AI Context (for LLMs/AI Crawlers)
python3 scripts/generate_llms_text.py

# Audit Internal Links (Suggestions for older pages)
# Note: If internal_link_auditor.py is missing, perform manual analysis of link opportunities.
# python3 scripts/internal_link_auditor.py <path_to_page>
```

## 2. Verify Updates
1.  **Sitemap**: Check `sitemap.xml` for well-formedness:
    ```bash
    python3 -c "import xml.etree.ElementTree as ET; ET.parse('sitemap.xml')"
    ```
2.  **LLM Context**: Verify the new page appears in `llms-full.txt` and `llms.txt`.
3.  **JSON-LD Schema**: Ensure the JSON-LD schema in the `<head>` of the updated page(s) has been synchronized with any factual changes made to the body text (Dates, Prices, Artists, etc.).
4.  **Internal Links & Breadcrumbs**: Review internal link opportunities and ensure the page has correctly implemented **Breadcrumbs** following the site hierarchy (e.g. `Home > News > Story`).

## When to use this:
- After adding any new `.html` file.
- After updating metadata (titles, descriptions, breadcrumbs).
- After making large structural changes to the site.
- After adding or updating news articles to ensure keyword priority, URL hierarchy (`/news/post`), and internal linking.
