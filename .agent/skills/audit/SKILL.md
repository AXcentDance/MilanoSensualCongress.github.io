---
name: audit
description: Audit this site's static health, Lighthouse scores, accessibility, SEO, and browser behavior using reproducible evidence; do not invent traffic or ranking data.
---

# Site audit

Use the domain, goal, and scope already supplied by the user/repository. Ask
only for missing information that affects a decision. Read the performance
rule for targets and measurement limits.

1. Record the working-tree state and baseline. Run
   `python3 scripts/run_all_checks.py` and `node --test tests/*.test.cjs`.
   Keep the individual checker's warnings visible as well as pass/fail.
2. For speed/browser work, run the pinned Lighthouse and Playwright gates.
   Attribute failures to specific pages, profiles, audits, and elements.
   Measure before changing assets, layout, loading, or integrations.
3. For SEO scope, inspect robots, canonical/hreflang reciprocity, sitemap
   coverage, internal links, headings, image alt text, social metadata, and
   structured data. Check live statuses/headers when delivery is in scope.
4. Make the smallest justified fix in both languages. Preserve the current
   look, URLs, event facts, forms, ticket links, and tracking requirements.
5. Regenerate affected derived files, run the static gate, then verify the
   affected behavior and repeat performance measurements when needed.

Report coverage and versions, before/after measurements, defects fixed,
pre-existing issues, limitations, and remaining decisions. Distinguish lab
scores from real-user Core Web Vitals and search performance. Do not fabricate
an overall SEO score from arbitrary weights or unsupported backlink/ranking
claims. Search Console/analytics data are optional evidence when available.

Judge content against visitor intent, accuracy, and usefulness. Title and
description length are presentation guides, not rigid quotas. Do not enforce
keyword density, filler word counts, or a fixed number of links. Use the
keyword skill only when the task includes research or targeting changes.
