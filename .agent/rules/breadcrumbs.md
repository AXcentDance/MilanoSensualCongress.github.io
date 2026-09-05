---
trigger: always_on
---

# Hidden breadcrumbs

- Every indexable subpage must retain a functional HTML breadcrumb trail and a matching `BreadcrumbList` in the page's unified JSON-LD graph. The homepages do not need an HTML trail.
- Breadcrumbs must always be hidden visually, on desktop and mobile. Keep the markup and links; do not delete the breadcrumb hierarchy to hide it.
- Use `<nav aria-label="Breadcrumb" hidden style="display:none!important">` so layout classes cannot reveal the trail. Hidden breadcrumb links must not create invisible keyboard focus stops or leave an empty layout gap.
- Apply this to both English and Italian pages, including older “Back to News” / “Torna alle News” breadcrumb links.
- This rule supersedes any older skill instruction requiring visible breadcrumbs.
