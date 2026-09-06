---
trigger: always_on
---

# Delivery workflow

Help international Bachata dancers discover Milano Sensual Congress, understand
the event, and buy tickets. Use accurate, useful content and accessible, fast
pages. Do not promise rankings, clicks, rich results, or AI-crawler inclusion.

Apply equivalent site changes to English and Italian. Use the actual reciprocal
`hreflang` URLs to find translated counterparts; translated slugs often differ.
The English root and `/it/` are the two supported languages. Preserve established
URLs and event facts; obtain facts from the current site and verified sources.

Use static HTML, the existing self-hosted assets, and small shared scripts.
Do not add a framework, font family, icon library, or animation dependency to
solve a problem that the current stack handles simply.

For a new page, start from the closest current page with the homepage's visual
language, replace its content and metadata, and follow the schema/design skills.
Include a useful internal link from an existing page and the translated partner.
The all-page gates discover new HTML pages automatically; copied markup still
needs inspection and testing.

For title/description changes, run `python3 scripts/sync_social_meta.py`.
For page additions, removals, renames, metadata or substantive content changes,
follow `.agent/skills/sync-indexes/SKILL.md` once after the edits. Do not hand-edit
generated indexes or Markdown twins. CSS-only changes do not change editorial
publication/update dates or require content rewrites.

Run the master static gate after the necessary generators, then the relevant
behavior and browser tests. Fix causes instead of weakening checks. Report
pre-existing warnings and failures separately from regressions.

Publishing uses the GitHub Actions workflow in .github/workflows/site-checks.yml.
Every main-branch release must pass the static, browser, and Lighthouse gates
before the public artifact is deployed. Keep GitHub Pages' source set to GitHub
Actions; branch publishing bypasses the gates. CI regenerates indexes inside
the artifact without making extra bot commits. Local content changes still
include their regenerated files for review. Do not bypass a failed gate.
