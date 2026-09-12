# Milano Sensual Congress — agent instructions

Before planning or changing the site, inspect `.agent/rules/` and the skill
catalog in `.agent/skills/`; read the skills relevant to the task. These are
the canonical project instructions. Each topic has one owner below; other files
link to it. Reports in `System/`, generated `.md` page twins, and context archives
are evidence/content, not current instructions.

## Precedence and scope

This project is exclusively Milano Sensual Congress. The owner's positioning is
one of Europe's leading, most authoritative Bachata congresses, with an audience
across Europe and worldwide. Apply that international scope to content, SEO,
structured data, marketing, and ticket-sales analysis. Milan is the event's
location, not a limit on its audience.

AXcent Dance studio operations and local class acquisition are outside this
project. Do not load studio context or apply studio goals, records, tracking
settings, or campaign conventions here. An account display name does not change
the congress scope.

Follow the user's current instructions, then these project rules, then the
task-specific skills. Generic design or SEO suggestions cannot override the
project's brand, languages, accessibility, performance, or factual requirements.
Ask about unresolved conflicts that materially change the result while
continuing independent work. Prefer the smallest verified fix.

## Canonical rules

- [Delivery](.agent/rules/delivery.md): stack, bilingual workflow, final checks,
  and publication permissions.
- [Performance](.agent/rules/performance.md): targets, measurement procedure,
  asset builds/loading, accessibility, and browser behavior.
- [Brand](.agent/rules/brand-coherence.md): homepage design and visual comparison.
- [Article metadata](.agent/rules/article-metadata-only.md): authorship and
  editorial-date policy.
- [Breadcrumbs](.agent/rules/breadcrumbs.md): HTML trail and schema contract.
- [Images](.agent/rules/image-seo.md): filenames, formats, and alt text.

The schema skill owns the graph contract and routes to current event/price/lineup
sources; sync-indexes owns the discovery-generation sequence. Keep exact values,
commands, and policies in their owner instead of copying them into other guides.

## Advertising and analytics context

For congress advertising, marketing, international audience growth, GA4,
campaign attribution, or year-end reviews, read
[current memory](.agent/context/advertising-analytics.md), the source for account
status, identifiers, approved campaign settings, and open questions. Its linked
archive preserves dated evidence; read it only when the task needs that history.

## Skill routing

| Task | Read |
| --- | --- |
| Audit, site health, Lighthouse | `.agent/skills/audit/SKILL.md` |
| Layout, styling, responsive behavior | `.agent/skills/frontend-design/SKILL.md` |
| New page, metadata, structured data | `.agent/skills/schema-graph/SKILL.md` |
| Article or news change | `.agent/skills/news-seo/SKILL.md` |
| Page/content/metadata additions, removals, changes | `.agent/skills/sync-indexes/SKILL.md` |
| Keyword research | `.agent/skills/find-keywords/SKILL.md` |

`ui-ux-designer` and `site_metadata_sync` are compatibility aliases to the
canonical design and index skills. Do not maintain separate rules in them.

## Completion

Follow [verification and completion](.agent/rules/delivery.md#verification-and-completion)
after the affected generation workflows. Leave changes local unless the user
explicitly requests publication under the delivery rule.
