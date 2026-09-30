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
`https://milanosensualcongress.com/#event` for the retained 2026 reference. The
announced 2027 edition has the distinct ID
`https://milanosensualcongress.com/#event-2027`; do not relabel 2026 offers,
performers or subevents as 2027. Give the local WebPage its canonical
URL plus `#webpage`; connect it to the WebSite and, on subpages, its `#breadcrumb`. Keep
subpage HTML/schema hierarchy consistent with the
[breadcrumb rule](../../rules/breadcrumbs.md). Omit homepage breadcrumb markup:
the homepage has no ancestors and Google's BreadcrumbList requires two items.

Select a primary entity that matches the page: Article/BlogPosting for an
article, ContactPage for contact, and the congress DanceEvent on its main event
page. A related congress entity in an article is not itself that article.
FAQ markup must match real questions and answers that visitors can access.
The canonical contact WebPage also has type ContactPage; do not create a second
anonymous page entity. Connect each article or course to its own WebPage as the
primary entity. The shared congress keeps the homepage as its event URL and
mainEntityOfPage, even when another page includes it as a related entity.

Keep congress admission offers separate from optional masterclass/competition
upgrades. Use Offer.addOn for conditional extras and never aggregate different
currencies. The admission Offer uses `/tickets#full-pass`; its masterclass add-on
uses `/tickets#masterclass-upgrade` on both translations, and CourseInstance.offers
references that same add-on. Announced future tiers have their own Offer identity
and a future validFrom/availabilityStarts; they do not replace current admission.
CourseInstance uses the actual teaching language, independently of
the page's translation, and date-only lesson bounds until precise times are
confirmed. Put verified learning duration on Course.timeRequired. Its own offer
describes the upgrade and the Full Pass prerequisite. Dance couples are
PerformingGroup entities with individual Person members; CourseInstance.instructor
references the people. Keep a couple's shared social profile on the group.
Do not add unrelated airport entities, invisible performer rosters, or FAQs
absent from the page merely to increase markup coverage.

## Current facts, not frozen templates

- `data/editions/2027.json` owns confirmed 2027 dates, venue and announcement
  status for the site and promotional materials. `scripts/edition_facts.py`
  validates this source against both homepage `#event-2027` graphs and visible
  `main #edition-facts` announcements, including their `<time datetime>` bounds.
  The homepage WebPage identifies 2027 as its main entity. Until additional
  details are confirmed, use date-only start/end values and omit offers,
  performers and subevents from this new event. The site may retain existing
  artists and media as clearly labelled reference material.
- `index.html` owns shared organization identity and the retained 2026
  `#event` dates, venue and ticket destination. `it/index.html` supplies
  translated copy. The visible
  `#congress-facts` paragraph on each homepage owns that language's statistics;
  these remain labelled as 2026 reference statistics. The LLM summary reads
  both editions through `scripts/event_facts.py` and `scripts/edition_facts.py`,
  introducing confirmed 2027 facts and distinguishing the older checkout,
  prices, schedules and statistics from unannounced 2027 arrangements.
  `scripts/check_event_facts.py` checks copied global event/organization facts
  and bilingual statistics quantities. Keep translations and subevents distinct.
  Timed facts accept valid `Z` or numeric offsets and compare the actual instant;
  the LLM summary renders event calendar dates in Europe/Rome. Preserve the
  original schema spelling and editorial timestamps.
- Read `scripts/update_price.py` for the canonical current Full Pass price and
  deadline. Use its `--check` gate. A price update must also reconcile visible
  tickets/copy/countdowns; the script does not update every visible price. The
  gate rejects expired admission even when all copies agree. It also owns the
  announced next-tier facts and checks the visible ticket cards. At rollover,
  promote the verified next tier and reconcile/remove its future announcement;
  this gate does not schedule publication or change the live site automatically.
- Read `artists.html` and `it/artists.html` for the current lineup. Reuse verified
  official profile URLs when available; do not invent social handles or require
  a fixed number of performers.
- A complete event uses actual name, confirmed start/end precision, status, attendance
  mode, venue/address, image, description, organizer, and current ticket offers.
  Keep timezone offsets on known event hours and timed deadlines. The 2027
  announcement deliberately omits unannounced admission and uses calendar dates
  without inventing hours. For article dates, follow the
  [article metadata rule](../../rules/article-metadata-only.md).
- Do not copy stale example prices, year-specific offers, or unverified facts
  into new pages. Do not add unsupported ratings or irrelevant schema types.

## Review visible copy when facts change

After changing event dates, venue, statistics, ticket destination, or the Full
Pass price/deadline, run this read-only review aid before final synchronization:

```bash
python3 scripts/check_event_facts.py --review-copy --base HEAD
```

For already committed edits, replace `HEAD` with the commit before those facts
changed. The report compares the homepage sources and canonical price constants,
then lists candidate public passages with file/line locations. Review their
translated counterparts and any schedule images/countdowns; reconcile current
sales copy and dates with the new source. Preserve clearly historical article
prices/dates, independent offers and other hotels/events when their context is
still accurate. Record the reviewed pages and intentional exceptions in the task
result. The report does not rewrite prose or certify factual accuracy; its
candidate matching is a search aid. If Git/source comparison fails, resolve it
or perform the same explicit review against the verified prior facts.

Use one canonical URL, reciprocal `en`/`it`/`x-default`, language-correct titles,
descriptions and `inLanguage`. Apply equivalent graph changes to both languages.
Follow [sync-indexes](../sync-indexes/SKILL.md) for social metadata and generated
files, then [delivery completion](../../rules/delivery.md#verification-and-completion).
The schema checks validate local invariants, not search-engine eligibility;
inspect warnings and verify official search documentation when making
eligibility claims.
