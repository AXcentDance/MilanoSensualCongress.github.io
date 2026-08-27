#!/usr/bin/env python3
"""Orphan-page check: every indexable page needs at least one inbound
internal link.

Builds the internal-link graph over all indexable pages (root, it/, news/,
it/news/). All href="" values count: body links (clean extensionless URLs
like ``artists``, ``./``, ``/it/tickets``, ``news/foo``), hreflang
alternates and the language switcher. A link only counts as inbound when it
comes from a *different* indexable page (self-references such as the
canonical tag do not rescue a page).

Fails (exit 1) listing any indexable page with zero inbound internal links;
404.html is exempt. Success marker: "no orphan pages".
"""
import glob
import os
import posixpath
import re
import sys
from urllib.parse import urlsplit

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_HOSTS = {'milanosensualcongress.com', 'www.milanosensualcongress.com'}

HREF_RE = re.compile(r'href=["\']([^"\']+)["\']')


def pages():
    return sorted(glob.glob('*.html') + glob.glob('it/*.html')
                  + glob.glob('news/*.html') + glob.glob('it/news/*.html'))


def resolve(href, source, page_set):
    """Map an href from `source` to a repo page path, or None if external/asset."""
    split = urlsplit(href)
    if split.scheme in ('mailto', 'tel', 'javascript', 'data'):
        return None
    if split.scheme in ('http', 'https'):
        if split.netloc.lower() not in SITE_HOSTS:
            return None
        path = split.path or '/'
    elif split.netloc:
        return None
    else:
        path = split.path
        if not path:          # pure fragment (#section) -> self, not a real link
            return None
        if not path.startswith('/'):
            path = '/' + posixpath.normpath(
                posixpath.join(posixpath.dirname('/' + source), path)).lstrip('/')
    # normalize the site-absolute path to a repo file
    path = posixpath.normpath(path)
    if path in ('/', '.'):
        candidates = ['index.html']
    else:
        rel = path.lstrip('/')
        candidates = []
        if href.rstrip().endswith('/') or not posixpath.splitext(rel)[1]:
            candidates += [rel.rstrip('/') + '/index.html', rel + '.html']
        if rel.endswith('.html'):
            candidates.append(rel)
    for cand in candidates:
        cand = posixpath.normpath(cand)
        if cand in page_set:
            return cand
    return None


def main():
    os.chdir(REPO_ROOT)
    all_pages = pages()
    html = {p: open(p, encoding='utf-8').read() for p in all_pages}
    indexable = [p for p in all_pages if 'noindex' not in html[p]]
    page_set = set(all_pages)

    inbound = {p: set() for p in all_pages}
    for source in indexable:
        for href in HREF_RE.findall(html[source]):
            target = resolve(href, source, page_set)
            if target and target != source:
                inbound[target].add(source)

    orphans = [p for p in indexable if p != '404.html' and not inbound[p]]
    if orphans:
        print(f'FAILED: {len(orphans)} orphan page(s) with zero inbound internal links:')
        for p in orphans:
            print(' -', p)
        sys.exit(1)
    print(f'no orphan pages ({len(indexable)} indexable pages all reachable '
          f'via internal links)')


if __name__ == '__main__':
    main()
