"""Canonical public-page and indexing policy for generators and quality tools.

Public HTML gets functional checks. Only indexable HTML gets search/LLM exports.
An intentional utility page needs both an entry below and a head robots noindex;
adding noindex to any other public page is an error, never a silent exclusion.
This policy selects files; noindex is not access control for private content.
"""
import os
from pathlib import Path
import re

from generation_support import GenerationError, read_page, run_generator, scan_error

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = {'node_modules', 'vendor', 'scripts', 'tests', 'System', 'test-results',
            'playwright-report', '__pycache__', 'output', 'tmp', 'google',
            'assets', 'images', 'css', 'js', 'fonts'}
NONINDEXED_PAGES = {'404.html': 'Public error page'}


def ignored_directory(name):
    return name.startswith('.') or name in EXCLUDED


def public_files(root=ROOT, suffix='.html'):
    root = Path(root)
    found = []
    for directory, dirs, files in os.walk(root, onerror=scan_error):
        dirs[:] = sorted(d for d in dirs if not ignored_directory(d))
        found.extend(Path(directory, name).relative_to(root).as_posix()
                     for name in files if not name.startswith('.') and name.endswith(suffix))
    return sorted(found)


def site_pages(root=ROOT):
    return public_files(root)


def restrictive_robots(soup):
    """Read actual robots tags, including multiple tags and the `none` alias.

    Google-specific restrictions must not silently remove a public search page.
    Utility approval still requires a general robots directive for all crawlers.
    """
    for meta in soup.find_all('meta'):
        name = meta.get('name', '').strip().lower()
        if name not in {'robots', 'googlebot'}:
            continue
        content = re.sub(r'\s*:\s*', ':', meta.get('content', '').lower())
        directives = set(re.split(r'[\s,]+', content.strip()))
        if directives & {'noindex', 'none'}:
            yield meta


def indexing_issues(page, soup):
    restrictions = list(restrictive_robots(soup))
    issues = []
    if restrictions and page not in NONINDEXED_PAGES:
        issues.append('unexpected noindex on public page')
    if any(meta.find_parent('head') is None for meta in restrictions):
        issues.append('robots indexing directives must be in the head')
    if page in NONINDEXED_PAGES and not any(
        meta.get('name', '').strip().lower() == 'robots'
        and meta.find_parent('head') is not None for meta in restrictions
    ):
        issues.append('approved nonindexed page must retain a head robots noindex directive')
    return issues


def page_is_indexable(page, soup):
    issues = indexing_issues(page, soup)
    if issues:
        raise GenerationError(f'{page}: {"; ".join(issues)}')
    return page not in NONINDEXED_PAGES


def classified_pages(root=ROOT):
    for page in site_pages(root):
        soup = read_page(Path(root) / page)
        yield page, soup, page_is_indexable(page, soup)


def indexable_pages(root=ROOT):
    return [page for page, _, indexable in classified_pages(root) if indexable]


def page_url_path(page):
    if page == 'index.html':
        return '/'
    if page.endswith('/index.html'):
        return '/' + page[:-len('index.html')]
    return '/' + page.removesuffix('.html')


def page_manifest(root=ROOT):
    return [{'file': page, 'path': page_url_path(page), 'indexable': indexable}
            for page, _, indexable in classified_pages(root)]


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--manifest', action='store_true')
    args = parser.parse_args()
    raise SystemExit(run_generator(lambda: print(json.dumps(
        page_manifest(args.root) if args.manifest else site_pages(args.root)))))
