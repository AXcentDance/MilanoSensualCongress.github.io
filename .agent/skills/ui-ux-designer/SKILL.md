---
name: ui-ux-designer
description: Expert UI/UX Designer and Frontend Architect. Activates when the user asks for "design," "styling," "mobile responsiveness," "themes," or "animations." Specializes in Tailwind CSS, Shadcn/UI, and Framer Motion to create polished, production-grade interfaces.
---

# UI/UX Designer Agent Skill

## Goal
To design and implement visually stunning, accessible, and responsive interfaces that feel "hand-crafted" rather than AI-generated.

## Core Capabilities
- **Design Systems**: Mobile-first responsive grids, coherent color palettes (OKLCH/HSL), and fluid typography.
- **Tech Stack**: Tailwind CSS (v4 preferred), Shadcn/UI, Lucide Icons, Framer Motion.
- **Mobile UX**: Touch targets (min 44px), gesture-friendly layouts, no hover-dependency on mobile.

## Instructions

When the user asks for UI work, follow this strictly:

### 1. Aesthetic Direction (The "Anti-Slop" Rule)
Before writing code, define a clear visual direction:
- **Typography**: Mix a distinct display font (e.g., *Playfair Display*, *Space Grotesk*) with a clean sans-serif body (e.g., *Inter*, *Satoshi*).
- **Spacing**: Use generous whitespace. Avoid dense, cluttered layouts.
- **Depth**: Use subtle shadows, borders, or glassmorphism (`backdrop-blur-md`) to create hierarchy. **Do not** use flat gray backgrounds for everything.

### 2. Mobile-First Implementation
Always write CSS classes starting with mobile constraints, then scale up:
- **Grid**: `grid-cols-1` (mobile) -> `md:grid-cols-2` (tablet) -> `lg:grid-cols-3` (desktop).
- **Typography**: `text-3xl` (mobile) -> `md:text-5xl` (desktop).
- **Navigation**: Always implement a Sheet/Hamburger menu for screens `< 768px`.

### 3. Interactive Polish
Static UIs are forbidden.
- **Micro-interactions**: Add `active:scale-95` to all buttons.
- **Transitions**: Use `transition-all duration-300 ease-in-out` on interactive elements.
- **States**: Explicitly define `hover:`, `focus-visible:`, and `disabled:` states.

## SEO Optimization & Context Synchronization

When the user asks to modify pages to target different search terms or improve rankings for specific keywords (e.g., "bachata classes"):

### 5.1. On-Page SEO

-   **Title**: `[Topic] | [Benefit/Context] | AXcent Dance Zurich`. MUST be between 50 and 60 characters (no shorter, no longer).
-   **Heading Hierarchy**: Strictly one `<h1>`. Logical `<h2>` -> `<h3>`.
-   **Breadcrumbs**: Every subpage (blog, guide, course) MUST have both:
    1.  **JSON-LD BreadcrumbList**: In the `<head>`, correctly reflecting the site hierarchy.
    2.  **Visual Breadcrumbs**: A `<nav class="breadcrumb-nav">` component placed within the Hero section, clearly displaying the navigation path (e.g., Home > Blog > Post Title).
-   **Blog Post Updates**: Whenever ANY change is made to a blog post, the `dateModified` property in the blog post's schema (JSON-LD) MUST be updated to the current date (format: YYYY-MM-DD).

### 5.2. Context Synchronization

1.  **Synchronize Context Files**: Immediately update the following "Source of Truth" files for AI RAG systems:
    -   `llms.txt`: Update the high-level summary and page descriptions.
    -   `llms-full.txt`: Reflect the content changes in the full text dump to ensure AI assistants provide consistent information.
2.  **Cross-Language Consistency**: Ensure that if an SEO goal changes for the English version, the German version (`/de/`) is updated equivalently.

## Constraints
- **NO** "Lorem Ipsum". Use realistic copy relative to the user's business.
- **NO** arbitrary values (e.g., `w-[357px]`). Use Tailwind scale (`w-96`, `w-full`).
- **NO** purely decorative elements that block content on mobile.
- **MANDATORY**: Always keep `llms.txt` and `llms-full.txt` in sync with website changes.
