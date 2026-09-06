#!/usr/bin/env python3
"""Inline per-page critical CSS and async-load the full stylesheets.

Two mechanisms live here:

1. Site-wide critical CSS (all indexable pages + 404.html, EN and IT).
   For every page that loads the shared stylesheets via <link> tags, the
   script builds a page-specific critical bundle:

     - all of css/fonts.css (font-face rules are needed immediately);
     - the subset of css/tailwind.min.css whose selectors reference only
       class names actually present in that page's HTML (class attributes
       plus class tokens quoted in inline scripts), a small safelist
       ('hidden', 'animate-spin'), and every selector with no class at all
       (html/body/:root/element preflight). @media/@supports blocks are
       filtered recursively; @keyframes are kept when referenced;
     - vendor/fontawesome/fa-subset.min.css filtered the same way (it is a
       flat list of single-class selectors with root-absolute font URLs, so
       the tailwind treatment is trivially safe for it);
     - all of css/site.css (small shared accessibility/responsive defaults).

   The bundle is injected as ONE marker block where the stylesheets sat:

     <style data-critical="HASH">...</style>

   where HASH is a stable content hash of the generated CSS plus the source
   CSS files. The shared stylesheet links are converted to the async pattern
   (media="print" onload="this.media='all'") with a single
   <noscript data-critical-fallback> block, so no render-blocking CSS
   request remains. Relative url() references are rewritten root-absolute.
   Existing ?v= query strings on the links are preserved verbatim.

   The transformation is idempotent: reruns recognise the marker block and
   the converted links and rewrite them in place.

2. Legacy fully-inlined art-directed pages (PAGES below) keep their
   <style data-inline="..."> blocks in sync with the source CSS files.
   Register new standalone art-directed pages in the PAGES dict.

Usage:

    python3 scripts/inline_critical_css.py            # rewrite all pages
    python3 scripts/inline_critical_css.py --check    # freshness gate

--check recomputes every hash without writing; it exits non-zero listing
stale or missing critical blocks, and on success prints the line
"critical css fresh".

Run this script after editing css/fonts.css, css/tailwind.min.css, css/site.css,
vendor/fontawesome/fa-subset.min.css, any CSS file listed in PAGES, or any
page's markup (class changes alter that page's critical subset).
"""
import argparse
import glob
import hashlib
import os
import re
import statistics
import sys
from site_files import site_pages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Shared stylesheets, in the order their <link> tags appear in every head.
# "full" sources are inlined wholesale; "purge" sources are filtered down to
# the selectors each page can actually match.
CRITICAL_SOURCES = [
    ("css/fonts.css", "full"),
    ("css/tailwind.min.css", "purge"),
    ("vendor/fontawesome/fa-subset.min.css", "purge"),
    ("css/site.css", "full"),
]

# Classes that scripts toggle at runtime and must always survive purging.
SAFELIST = {"hidden", "animate-spin"}

# Warn when a page's generated critical CSS exceeds this many bytes.
WARN_BYTES = 40 * 1024

HASH_LEN = 16

# Page globs that make up the indexable site (plus 404.html, which renders
# for users). .claude/, vendor/, node_modules/ and worktrees are never
# matched by these patterns.
PAGE_GLOBS = ["*.html", "it/*.html", "news/*.html", "it/news/*.html"]

# Legacy pages that inline their CSS wholesale via <style data-inline="...">
# markers. These pages have no stylesheet <link> tags at all, so the
# critical-CSS pipeline skips them.
PAGES = {
    "news/bachata-workshop-levels-guide-congress.html": [
        "css/fonts.css",
        "css/workshop-levels-guide.css",
        "css/site.css",
    ],
    "it/news/livelli-workshop-bachata-congresso.html": [
        "css/fonts.css",
        "css/workshop-levels-guide.css",
        "css/site.css",
    ],
    "news/bachata-congress-alone-solo-dancer-guide.html": [
        "css/fonts.css",
        "css/solo-congress-guide.css",
        "css/site.css",
    ],
    "it/news/congresso-bachata-da-soli-guida-ballerini.html": [
        "css/fonts.css",
        "css/solo-congress-guide.css",
        "css/site.css",
    ],
}

# ---------------------------------------------------------------------------
# CSS parsing
# ---------------------------------------------------------------------------


def split_rules(css):
    """Split a stylesheet into top-level nodes.

    Yields ("stmt", prelude) for @charset/@import style statements and
    ("block", prelude, body) for braced rules. String literals and nested
    braces are respected; comments are dropped.
    """
    nodes = []
    i, n = 0, len(css)
    while i < n:
        while i < n and css[i].isspace():
            i += 1
        if i >= n:
            break
        if css.startswith("/*", i):
            j = css.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        j = i
        in_str = None
        while j < n:
            c = css[j]
            if in_str:
                if c == "\\":
                    j += 1
                elif c == in_str:
                    in_str = None
            elif c == "\\":
                # Escaped character outside a string (e.g. \' in Tailwind
                # arbitrary-value selectors) — never opens a string.
                j += 1
            elif c in "\"'":
                in_str = c
            elif c == "{" or c == ";":
                break
            j += 1
        prelude = css[i:j].strip()
        if j >= n:
            if prelude:
                nodes.append(("stmt", prelude))
            break
        if css[j] == ";":
            if prelude:
                nodes.append(("stmt", prelude))
            i = j + 1
            continue
        depth, k, in_str = 1, j + 1, None
        while k < n and depth:
            c = css[k]
            if in_str:
                if c == "\\":
                    k += 1
                elif c == in_str:
                    in_str = None
            elif c == "\\":
                k += 1
            elif c in "\"'":
                in_str = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            k += 1
        nodes.append(("block", prelude, css[j + 1 : k - 1]))
        i = k
    return nodes


# Class token inside a selector; tolerates identity escapes (\:) and CSS hex
# escapes (\32 ) for classes starting with a digit.
CLASS_TOKEN_RE = re.compile(r"\.((?:\\[0-9a-fA-F]{1,6} ?|\\.|[A-Za-z0-9_-])+)")


def unescape_class(token):
    out, i = [], 0
    while i < len(token):
        if token[i] == "\\":
            m = re.match(r"\\([0-9a-fA-F]{1,6}) ?", token[i:])
            if m:
                out.append(chr(int(m.group(1), 16)))
                i += m.end()
                continue
            if i + 1 < len(token):
                out.append(token[i + 1])
            i += 2
            continue
        out.append(token[i])
        i += 1
    return "".join(out)


def split_selectors(selector_list):
    """Split a selector list on top-level commas."""
    parts, cur, depth, in_str, escaped = [], [], 0, None, False
    for ch in selector_list:
        if escaped:
            cur.append(ch)
            escaped = False
            continue
        if ch == "\\":
            cur.append(ch)
            escaped = True
            continue
        if in_str:
            cur.append(ch)
            if ch == in_str:
                in_str = None
            continue
        if ch in "\"'":
            in_str = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def selector_classes(selector):
    return {unescape_class(t) for t in CLASS_TOKEN_RE.findall(selector)}


def keep_selector(selector, classes):
    used = selector_classes(selector)
    return not used or used <= classes


URL_RE = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)")


def rewrite_urls(css, base):
    """Rewrite relative url() references to root-absolute paths."""

    def repl(m):
        quote, target = m.groups()
        if target.startswith(("/", "#", "data:", "http://", "https://")):
            return m.group(0)
        path = os.path.normpath(os.path.join(base, target)).replace(os.sep, "/")
        if not path.startswith("/"):
            path = "/" + path
        return "url(%s%s%s)" % (quote, path, quote)

    return URL_RE.sub(repl, css)


def filter_css(css, classes, keyframes, base):
    """Keep only rules whose selectors this page can match.

    @keyframes rules are collected into `keyframes` (name -> text) instead
    of being emitted; the caller appends the referenced ones.
    """
    out = []
    for node in split_rules(css):
        if node[0] == "stmt":
            out.append(node[1] + ";")
            continue
        prelude, body = node[1], node[2]
        low = prelude.lower()
        if low.startswith("@media") or low.startswith("@supports"):
            inner = filter_css(body, classes, keyframes, base)
            if inner:
                out.append("%s{%s}" % (prelude, inner))
        elif low.startswith("@keyframes") or low.startswith("@-webkit-keyframes"):
            name = prelude.split()[-1]
            keyframes.setdefault(name, "%s{%s}" % (prelude, body))
        elif low.startswith("@font-face") or low.startswith("@"):
            out.append("%s{%s}" % (prelude, rewrite_urls(body, base)))
        else:
            kept = [s for s in split_selectors(prelude) if keep_selector(s, classes)]
            if kept:
                out.append("%s{%s}" % (",".join(kept), rewrite_urls(body, base)))
    return "".join(out)


COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


def light_minify(css):
    """Strip comments and collapse whitespace runs to single spaces."""
    css = COMMENT_RE.sub("", css)
    return re.sub(r"\s+", " ", css).strip()


# ---------------------------------------------------------------------------
# Page class collection
# ---------------------------------------------------------------------------

CLASS_ATTR_RE = re.compile(r"""class\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
INLINE_SCRIPT_RE = re.compile(
    r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.S | re.I
)
STRING_LIT_RE = re.compile(r"""["']([^"'\\\n]{1,80})["']""")


def collect_page_classes(html, css_universe):
    """All class names a page can carry: markup plus inline-script toggles."""
    classes = set(SAFELIST)
    for m in CLASS_ATTR_RE.finditer(html):
        classes.update((m.group(1) or m.group(2) or "").split())
    for m in INLINE_SCRIPT_RE.finditer(html):
        for literal in STRING_LIT_RE.findall(m.group(1)):
            for token in literal.split():
                if token in css_universe:
                    classes.add(token)
    return classes


def css_class_universe(sources):
    """Every class name defined by the purgeable stylesheets."""
    universe = set()

    def walk(css):
        for node in split_rules(css):
            if node[0] != "block":
                continue
            prelude, body = node[1], node[2]
            if prelude.lower().startswith(("@media", "@supports")):
                walk(body)
            elif not prelude.startswith("@"):
                universe.update(selector_classes(prelude))

    for path, mode in CRITICAL_SOURCES:
        if mode == "purge":
            walk(sources[path])
    return universe


# ---------------------------------------------------------------------------
# Critical CSS generation
# ---------------------------------------------------------------------------


def build_critical_css(html, sources, css_universe):
    classes = collect_page_classes(html, css_universe)
    keyframes = {}
    parts = []
    for path, mode in CRITICAL_SOURCES:
        base = "/" + os.path.dirname(path)
        css = sources[path]
        if mode == "full":
            parts.append(rewrite_urls(light_minify(css), base))
        else:
            parts.append(filter_css(css, classes, keyframes, base))
    body = "".join(parts)
    haystack = body + " " + html
    for name, text in keyframes.items():
        if re.search(r"\b%s\b" % re.escape(name), haystack):
            body += text
    return body


def critical_hash(critical_css, sources):
    h = hashlib.sha256()
    h.update(critical_css.encode("utf-8"))
    for path, _mode in CRITICAL_SOURCES:
        h.update(b"\0")
        h.update(sources[path].encode("utf-8"))
    return h.hexdigest()[:HASH_LEN]


# ---------------------------------------------------------------------------
# HTML transformation
# ---------------------------------------------------------------------------

LINK_TAG_RE = re.compile(r'<link rel="stylesheet" href="[^"]+"[^>]*>')
HREF_RE = re.compile(r'href="([^"]+)"')
CONVERTED_RE = re.compile(
    r'([ \t]*)<style data-critical="[0-9a-f]{%d}">.*?</style>\s*'
    r'(?:<link rel="stylesheet"[^>]*>\s*)*'
    r"<noscript data-critical-fallback>.*?</noscript>" % HASH_LEN,
    re.S,
)
DATA_CRITICAL_RE = re.compile(r'<style data-critical="([0-9a-f]+)">')


def build_block(indent, critical_css, digest, hrefs):
    lines = ['%s<style data-critical="%s">%s</style>' % (indent, digest, critical_css)]
    for href in hrefs:
        lines.append(
            '%s<link rel="stylesheet" href="%s" media="print" '
            "onload=\"this.media='all'\">" % (indent, href)
        )
    fallback = "".join('<link rel="stylesheet" href="%s">' % h for h in hrefs)
    lines.append(
        "%s<noscript data-critical-fallback>%s</noscript>" % (indent, fallback)
    )
    return "\n".join(lines)


def find_region(html, page):
    """Locate the stylesheet region. Returns (start, end, indent, hrefs)."""
    m = CONVERTED_RE.search(html)
    if m:
        noscript = re.search(
            r"<noscript data-critical-fallback>(.*?)</noscript>", m.group(0), re.S
        )
        hrefs = HREF_RE.findall(noscript.group(1))
        return m.start(), m.end(), m.group(1), hrefs
    tags = list(LINK_TAG_RE.finditer(html))
    if not tags:
        return None
    start, end = tags[0].start(), tags[-1].end()
    between = LINK_TAG_RE.sub("", html[start:end])
    if between.strip():
        raise ValueError(
            "%s: stylesheet <link> tags are not contiguous; refusing to rewrite"
            % page
        )
    hrefs = [HREF_RE.search(t.group(0)).group(1) for t in tags]
    line_start = html.rfind("\n", 0, start) + 1
    indent = html[line_start:start]
    if indent.strip() == "":
        start = line_start
    else:
        indent = ""
    return start, end, indent, hrefs


def expected_basenames():
    return [os.path.basename(p) for p, _m in CRITICAL_SOURCES]


def process_page(page, sources, css_universe, check):
    """Returns (ok, size_bytes or None, changed)."""
    path = os.path.join(ROOT, page)
    with open(path, encoding="utf-8") as f:
        html = f.read()

    try:
        region = find_region(html, page)
    except ValueError as exc:
        print("ERROR: %s" % exc)
        return False, None, False
    if region is None:
        print("ERROR: %s has no stylesheet links and no critical block" % page)
        return False, None, False
    start, end, indent, hrefs = region

    names = [os.path.basename(h.split("?")[0]) for h in hrefs]
    if names != expected_basenames():
        print("ERROR: %s links unexpected stylesheets: %s" % (page, names))
        return False, None, False

    critical = build_critical_css(html, sources, css_universe)
    digest = critical_hash(critical, sources)
    size = len(critical.encode("utf-8"))
    if size > WARN_BYTES:
        print(
            "WARNING: %s critical css is %.1fKB (limit %dKB)"
            % (page, size / 1024.0, WARN_BYTES // 1024)
        )

    if check:
        found = DATA_CRITICAL_RE.findall(html)
        content = re.search(r'<style data-critical="[0-9a-f]+">(.*?)</style>', html, re.S)
        if len(found) != 1 or found[0] != digest or not content or content.group(1) != critical:
            state = "missing" if not found else "stale"
            print("STALE: %s critical block is %s" % (page, state))
            return False, size, False
        return True, size, False

    block = build_block(indent, critical, digest, hrefs)
    new_html = html[:start] + block + html[end:]
    changed = new_html != html
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_html)
    print("%s: %s (%.1fKB)" % (page, "updated" if changed else "in sync", size / 1024.0))
    return True, size, changed


# ---------------------------------------------------------------------------
# Legacy data-inline pages
# ---------------------------------------------------------------------------


def sync_data_inline_page(page, css_files, check):
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
        replacement = r"\g<1>\n%s\n  \g<2>" % content.replace("\\", "\\\\")
        new_html, count = pattern.subn(replacement, html)
        if count != 1:
            print("ERROR: expected 1 marker for %s in %s, found %d" % (css, page, count))
            return False
        if new_html != html:
            changed = True
            html = new_html
    if check:
        if changed:
            print("STALE: %s data-inline blocks out of sync" % page)
            return False
        return True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    print("%s: %s (data-inline)" % (page, "updated" if changed else "in sync"))
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def iter_pages():
    return [page for page in site_pages() if page not in PAGES]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify freshness without writing; exit non-zero when stale",
    )
    args = parser.parse_args()

    sources = {}
    for path, _mode in CRITICAL_SOURCES:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            sources[path] = f.read()
    css_universe = css_class_universe(sources)

    ok = True
    sizes = []
    for page in iter_pages():
        page_ok, size, _changed = process_page(
            page, sources, css_universe, check=args.check
        )
        ok = page_ok and ok
        if size is not None:
            sizes.append(size)
    for page, css_files in PAGES.items():
        ok = sync_data_inline_page(page, css_files, check=args.check) and ok

    if sizes:
        print(
            "critical css sizes: min %.1fKB / median %.1fKB / max %.1fKB "
            "across %d pages"
            % (
                min(sizes) / 1024.0,
                statistics.median(sizes) / 1024.0,
                max(sizes) / 1024.0,
                len(sizes),
            )
        )
    if args.check:
        if ok:
            print("critical css fresh")
        else:
            print("critical css STALE: rerun python3 scripts/inline_critical_css.py")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
