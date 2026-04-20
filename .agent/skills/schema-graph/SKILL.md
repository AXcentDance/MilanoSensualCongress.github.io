---
name: schema-graph
description: Guidelines for implementing a unified JSON-LD @graph structure for SEO and AI discoverability.
---

# Schema Graph Standard Implementation

Use this skill whenever you are modifying a page's metadata, adding a new page, or fixing SEO issues. This ensures that search engines (Google) and AI crawlers (Perplexity, OpenAI O1, Gemini) understand the semantic relationship between entities on your site.

## 1. Core Principles
*   **One Tag to Rule Them All**: Use exactly ONE `<script type="application/ld+json">` tag in the `<head>`. 
*   **Unified Graph Mandate**: Any entity that CAN be part of the schema (FAQ, Events, BlogPosting, Organization, etc.) MUST be contained within the top-level `@graph` array.
*   **Strict Consolidation**: Standalone JSON-LD tags elsewhere in the HTML are FORBIDDEN. If you find one, it must be merged into the head’s graph.
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
*   **Home/News Pages**: `DanceEvent` (the main congress). 
    *   **GSC MANDATORY**: Every `DanceEvent` MUST include:
        *   `offers`: Complete specification (prices and ticket URL).
        *   `location`: Full `Place` object for "Devero Hotel".
        *   `name`, `startDate`, `endDate`, `image`, `description`.
    *   **RECOMMENDED**: `performer` array with all 8 main artists and their `sameAs` links.
*   **News Articles**: `BlogPosting` + `DanceEvent` (Consolidated in the same graph).
*   **Contact Page**: `ContactPage`.
*   **FAQ Sections**: `FAQPage`.
*   **Hotel/Tickets**: `WebPage` with detailed `mainEntity` or specific sub-entities.

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



## 7. Global Artist Entity Linking
When referencing top-tier performers in `DanceEvent` or `Person` JSON-LD schema (e.g., Gero y Migle, Klau y Ros), you MUST use the `sameAs` explicit mapping linked to their official Instagram or core digital entity to bridge into Google's Knowledge Graph.

## 8. Gold-Standard DanceEvent Template
Use this exact structure for all pages requiring the congress entity:

```json
{
  "@type": "DanceEvent",
  "@id": "https://milanosensualcongress.com/#event",
  "name": "Milano Sensual Congress 2026",
  "startDate": "2026-11-20T18:00:00+01:00",
  "endDate": "2026-11-22T23:59:59+01:00",
  "eventStatus": "https://schema.org/EventScheduled",
  "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
  "location": {
    "@type": "Place",
    "name": "Devero Hotel",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "Largo Kennedy, 1",
      "addressLocality": "Cavenago di Brianza",
      "postalCode": "20873",
      "addressRegion": "MB",
      "addressCountry": "IT"
    }
  },
  "image": ["https://milanosensualcongress.com/images/logo.webp"],
  "description": "The ultimate Bachata experience in Italy. World-class lineup, executive venue, and unforgettable parties.",
  "organizer": { "@id": "https://milanosensualcongress.com/#organization" },
  "performer": [
    { "@type": "Person", "name": "Gero y Migle", "sameAs": "https://www.instagram.com/geroymigle_official/" },
    { "@type": "Person", "name": "Klaus y Ros", "sameAs": "https://www.instagram.com/klausyros/" },
    { "@type": "Person", "name": "Cristian y Gabriella", "sameAs": "https://www.instagram.com/cristianygabriella_official/" },
    { "@type": "Person", "name": "David y Ines", "sameAs": "https://www.instagram.com/davidyines/" },
    { "@type": "Person", "name": "Nacho y Silvia", "sameAs": "https://www.instagram.com/nachoysilvia/" },
    { "@type": "Person", "name": "Agustín y Alba", "sameAs": "https://www.instagram.com/agustinyalba_official/" },
    { "@type": "Person", "name": "Irene y Tomás", "sameAs": "https://www.instagram.com/ireneytomas/" },
    { "@type": "Person", "name": "Aitor Gomez", "sameAs": "https://www.instagram.com/aitorgomez_bachata/" }
  ],
  "offers": {
    "@type": "Offer",
    "url": "https://lasalsadelbaile.com/MSC2026",
    "priceCurrency": "EUR",
    "availability": "https://schema.org/InStock",
    "priceSpecification": [
      {
        "@type": "UnitPriceSpecification",
        "name": "Early-Bird Full Pass",
        "price": "110.00",
        "priceCurrency": "EUR",
        "validThrough": "2026-04-30T23:59:59"
      },
      {
        "@type": "UnitPriceSpecification",
        "name": "Standard Full Pass",
        "price": "135.00",
        "priceCurrency": "EUR",
        "validFrom": "2026-05-01T00:00:00"
      }
    ]
  }
}
```
