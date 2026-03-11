# Site Metadata Sync Skill

This skill ensures that the website's SEO and AI-context metadata files are always up-to-date.

## Purpose
Whenever a page is added, removed, or significantly changed, the following files must be regenerated:
1. `sitemap.xml`: For search engines to discover new content.
2. `llms-full.txt`: Full content dump for AI crawlers and agents.
3. `llms.txt`: Summary of the site for AI agents.

## When to Run
- After creating a new `.html` page.
- After deleting an `.html` page.
- After updating metadata (title, description) or significant content on any page.
- Before finishing a task that involves structural changes.

## How to execute
Run the following commands from the root directory:

```bash
python3 scripts/generate_sitemap.py
python3 scripts/generate_llms_text.py
```

## Troubleshooting
- If `BeautifulSoup` is missing, the scripts will attempt to use regex fallbacks, but for best results, ensure `bs4` is installed: `pip install beautifulsoup4`.
- Ensure you are in the root directory of the project when running the scripts.
