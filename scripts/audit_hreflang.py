#!/usr/bin/env python3
"""Check complete, genuinely reciprocal language clusters on every public page."""
import sys
from bs4 import BeautifulSoup
from site_files import ROOT, site_pages


def validate_clusters(pages):
    issues = []
    by_url = {data['canonical']: data for data in pages.values()}
    for name, page in pages.items():
        links = page['links']
        language = 'it' if name.startswith('it/') else 'en'
        if links.get(language) != page['canonical']:
            issues.append(f'{name}: own-language hreflang must equal canonical')
        if links.get('x-default') != links.get('en'):
            issues.append(f'{name}: x-default must identify the English counterpart')
        for lang in ['en', 'it', 'x-default']:
            target = by_url.get(links.get(lang))
            if target is None:
                issues.append(f'{name}: {lang} does not resolve to an indexable canonical page')
            elif target['links'] != links:
                issues.append(f'{name}: {lang} target does not link back to the same EN/IT cluster')
    return issues


def main():
    pages = {}
    for name in site_pages():
        soup = BeautifulSoup((ROOT / name).read_text(), 'html.parser')
        if any('noindex' in meta.get('content', '') for meta in soup.select('meta[name="robots"]')):
            continue
        canonical = soup.select_one('link[rel="canonical"]')
        pages[name] = {
            'canonical': canonical.get('href') if canonical else None,
            'links': {tag.get('hreflang'): tag.get('href') for tag in soup.select('head link[rel="alternate"][hreflang]')},
        }
    issues = validate_clusters(pages)
    if issues:
        print('\n'.join(issues))
        return 1
    print(f'{len(pages)} indexable pages: hreflang clusters are perfectly reciprocal')
    return 0


if __name__ == '__main__':
    sys.exit(main())
