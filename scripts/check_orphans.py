#!/usr/bin/env python3
"""Every indexable page must be reachable from a homepage via HTML links.
Hreflang metadata and isolated pairs of translated pages cannot rescue orphans.
"""
from site_files import site_pages
import os
import posixpath
import re
import sys
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_HOSTS = {'milanosensualcongress.com', 'www.milanosensualcongress.com'}

def pages():
    return site_pages()


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


def unreachable_pages(html):
    parsed = {page: BeautifulSoup(content, 'html.parser') for page, content in html.items()}
    indexable = {page for page, soup in parsed.items() if not any(
        'noindex' in meta.get('content', '').lower()
        for meta in soup.find_all('meta', attrs={'name': 'robots'}))}
    graph = {page: set() for page in indexable}
    for source in indexable:
        body = parsed[source].body
        for link in body.find_all('a', href=True) if body else []:
            target = resolve(link['href'], source, indexable)
            if target:
                graph[source].add(target)
    pending = list(indexable & {'index.html', 'it/index.html'})
    reached = set()
    while pending:
        page = pending.pop()
        if page not in reached:
            reached.add(page)
            pending.extend(graph[page] - reached)
    return sorted(indexable - reached)


def main():
    os.chdir(REPO_ROOT)
    html = {page: open(page, encoding='utf-8').read() for page in pages()}
    orphans = unreachable_pages(html)
    if orphans:
        print(f'FAILED: {len(orphans)} page(s) unreachable from the homepages:')
        for p in orphans:
            print(' -', p)
        sys.exit(1)
    print('no orphan pages (all indexable pages reachable via HTML links from the homepages)')


if __name__ == '__main__':
    main()
