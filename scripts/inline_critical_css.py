#!/usr/bin/env python3
"""Inline page-critical CSS into <style data-inline="..."> blocks.

Standalone art-directed pages (currently the solo dancer guides) inline their
CSS instead of loading it via render-blocking <link> tags, which removes two
round trips from the LCP critical chain on slow connections.

The inlined copy lives inside a marker tag:

    <style data-inline="css/solo-congress-guide.css">...</style>

IMPORTANT: after editing any CSS file listed below, re-run this script so the
inlined copies stay in sync:

    python3 scripts/inline_critical_css.py

The script is idempotent and rewrites only the marked blocks.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pages that carry inlined CSS. Each entry lists the CSS files in the order
# their <style data-inline> blocks appear in the page head.
PAGES = {
    "news/bachata-congress-alone-solo-dancer-guide.html": [
        "css/fonts.css",
        "css/solo-congress-guide.css",
    ],
    "it/news/congresso-bachata-da-soli-guida-ballerini.html": [
        "css/fonts.css",
        "css/solo-congress-guide.css",
    ],
}


def inline_page(page, css_files):
    path = os.path.join(ROOT, page)
    with open(path, encoding="utf-8") as f:
        html = f.read()
    changed = False
    for css in css_files:
        with open(os.path.join(ROOT, css), encoding="utf-8") as f:
            content = f.read().strip()
        # Font URLs are root-absolute (/fonts/...), so no path rewriting needed.
        pattern = re.compile(
            r'(<style data-inline="%s">).*?(</style>)' % re.escape(css), re.S
        )
        replacement = r"\g<1>\n%s\n  \g<2>" % content
        new_html, count = pattern.subn(replacement, html)
        if count != 1:
            print(f"ERROR: expected 1 marker for {css} in {page}, found {count}")
            return False
        if new_html != html:
            changed = True
            html = new_html
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{page}: {'updated' if changed else 'already in sync'}")
    return True


def main():
    ok = True
    for page, css_files in PAGES.items():
        ok = inline_page(page, css_files) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
