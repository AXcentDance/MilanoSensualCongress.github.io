---
name: schema-graph
description: Guidelines for implementing a unified JSON-LD @graph structure for SEO and AI discoverability.
---

# Schema Graph Standard Implementation

Use this skill whenever you are modifying a page's metadata, adding a new page, or fixing SEO issues. This ensures that search engines (Google) and AI crawlers (Perplexity, OpenAI O1, Gemini) understand the semantic relationship between entities on your site.

## 1. Core Principles
*   **One Tag to Rule Them All**: Use exactly one `<script type="application/ld+json">` tag in the `<head>`.
*   **The @graph Array**: All entities must be contained within a top-level `@graph` array.
*   **Persistent Identifiers (@id)**: Use canonical URLs with fragments (e.g., `#organization`, `#website`, `#webpage`) to cross-reference entities across the entire site.

## 2. Standard Global Entities
Every page graph should reference these global entities for consistency:

*   **Organization**: `https://milanosensualcongress.com/#organization`
*   **WebSite**: `https://milanosensualcongress.com/#website`

## 3. Mandatory Page-Specific Entities
Every page must have:
*   **WebPage**: Connected to the WebSite via `isPartOf`. Use the canonical URL with `#webpage` as the ID.
*   **BreadcrumbList**: Connected to the WebPage. Use `#breadcrumb` as the ID.

## 4. Entity Specifics (Rich Snippets)
Add the specific type of content for the page as a primary entity in the graph:
*   **Home Page**: `DanceEvent` (the main congress).
*   **News Articles**: `BlogPosting`.
*   **Contact Page**: `ContactPage`.
*   **FAQ Sections**: `FAQPage`.
*   **Hotel/Tickets**: `WebPage` with detailed `mainEntity`.

## 5. Implementation Template
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://milanosensualcongress.com/#organization",
      "name": "Milano Sensual Congress",
      "url": "https://milanosensualcongress.com",
      "logo": "https://milanosensualcongress.com/images/logo.webp",
      "sameAs": [
        "https://www.instagram.com/milano_sensual_congress/"
      ]
    },
    {
      "@type": "WebSite",
      "@id": "https://milanosensualcongress.com/#website",
      "url": "https://milanosensualcongress.com",
      "name": "Milano Sensual Congress",
      "publisher": { "@id": "https://milanosensualcongress.com/#organization" }
    },
    {
      "@type": "WebPage",
      "@id": "[CANONICAL_URL]#webpage",
      "url": "[CANONICAL_URL]",
      "name": "[PAGE_TITLE]",
      "isPartOf": { "@id": "https://milanosensualcongress.com/#website" },
      "breadcrumb": { "@id": "[CANONICAL_URL]#breadcrumb" },
      "inLanguage": "[en-US|it-IT]"
    },
    {
      "@type": "BreadcrumbList",
      "@id": "[CANONICAL_URL]#breadcrumb",
      "itemListElement": [...]
    },
    {
      "@type": "[SpecificType - e.g. DanceEvent]",
      "mainEntityOfPage": { "@id": "[CANONICAL_URL]#webpage" },
      "name": "...",
      ...
    }
  ]
}
```

## 6. Bilingual Consistency (Rule `it.md`)
Whenever updating the `@graph` on an English page, immediately apply the same structural change to its Italian counterpart in `/it/`. Ensure the `inLanguage` property and all translated fields match the respective versions.
