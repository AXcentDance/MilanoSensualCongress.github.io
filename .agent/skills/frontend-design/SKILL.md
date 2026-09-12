---
name: frontend-design
description: Change Milano Sensual Congress layouts, styling, navigation, and responsive behavior within the existing homepage brand and performance requirements.
---

# Site design

Follow the [homepage brand rule](../../rules/brand-coherence.md) for reference
files, palette, typography, and shared components, and the
[performance rule](../../rules/performance.md) for loading and interactions.

Keep layout changes proportional to the issue; do not redesign for novelty.
Use the existing stack described in [delivery](../../rules/delivery.md).

Implement and inspect both languages at the brand rule's required widths.
Let navigation breakpoints follow the space its links actually need. Check logo proportions,
text wrapping, tap targets, keyboard focus, reduced motion, and horizontal
overflow. Test open menus and controls as well as the initial screen.

After class/CSS changes, follow the performance rule's
[build and critical-CSS steps](../../rules/performance.md#render-and-load).
Preserve content and metadata unless the task requires changes, including the
[editorial date policy](../../rules/article-metadata-only.md). When content or
metadata changes, use [sync-indexes](../sync-indexes/SKILL.md). Finish with
[delivery completion](../../rules/delivery.md#verification-and-completion).
