---
name: news-seo
description: Guidelines for creating SEO-optimized news articles with strong internal linking and high-priority bachata keywords.
---

# News SEO & Internal Linking

Use this skill whenever you are adding a new news article, blog post, or update to the timeline. This ensures maximum search engine visibility and site connectivity.

## 1. SEO Keyword Priority
Always prioritize the following keywords and their semantic variations to rank at the top for people searching for dance events:
- **Core Keywords**: `Bachata Congress`, `Bachata Events`, `Bachata Festivals`, `Bachata Workshop`.
- **Secondary Keywords**: `Latin Festivals in Europe`, `Bachata Sensual Italy`, `Milano Dance Events 2026`.
- **Action**: Include at least 2-3 of these in the `<title>`, `<h1>`, and meta `<description>`.

## 2. Internal Linking Mandate
Every news article must be "well-connected" to the rest of the website to share authority:
- **Outbound Links**: Link from the article to core pages like [Tickets](tickets.html), [Artists](artists.html), [Hotel](hotel.html), and [Transfer](transfer.html).
- **Inbound Links**: When adding a news article, look for opportunities to link *to it* from the Homepage or relevant older articles to boost its crawlability.
- **Link Text**: Use descriptive anchor text (e.g., "Check out the full [Bachata Artists line-up](artists.html)") instead of generic "click here".

## 3. Bilingual Requirement
As per the project's global rules, every news change must be applied identically to:
- `/news.html` (English)
- `/it/news.html` (Italian)
And any supporting sub-pages in their respective language directories.

## 4. Meta-Data & Schema
- Update the `llms.txt` and `llms-full.txt` after adding news content using the `sync-indexes` skill.
- Ensure the news article has a relevant `date` in both English and Italian formats.
- **JSON-LD Comprehensive Schema**:
    - You MUST inject a complete JSON-LD `<script>` tag in the `<head>` structured as an array containing multiple schemas.
    - Include a `BlogPosting` object with: `mainEntityOfPage`, `headline`, `image`, `author` (Organization), `publisher` (Organization with logo), `datePublished`, `dateModified`, and `description`. Use strict ISO 8601 formatting for dates (e.g., `2026-03-14T09:00:00+01:00`). 
    - Include a `BreadcrumbList` object outlining the site hierarchy (e.g., `Home > News > [Post Title]`).
- **Visual Breadcrumbs**: In addition to JSON-LD, implement visible breadcrumb links (e.g., "Back to News") at the top of the article.

## 5. URL Structure
- Every news article file should be located within a relevant directory structure or logically mapped.
- **Mandatory Parent**: News articles must be children of the News page in the breadcrumb hierarchy.

## 6. Visuals
- Use realistic, high-quality images. Avoid generic or "obviously AI" graphics. If generating AI images, use prompts that emphasize realism and professional photography.
