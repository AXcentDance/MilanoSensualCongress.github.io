#!/usr/bin/env python3
"""Check local non-image sources and HTML CSS resources on public pages.

Image src validation belongs to check_image_seo; href validation to audit_links.
This checker retains the old asset audit's complementary script/video/source
and CSS url(...) coverage without another public-page exclusion list.
"""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from site_files import ROOT, site_pages

CSS_URL = re.compile(r'''url\(\s*["']?([^"')]+)''', re.I)


def resource_references(soup):
    for node in soup.find_all(src=True):
        if node.name != 'img':
            yield node['src']
    for style in soup.find_all('style'):
        yield from CSS_URL.findall(style.string or style.get_text())
    for node in soup.find_all(style=True):
        yield from CSS_URL.findall(node['style'])


def audit_assets(root=ROOT):
    root = Path(root).resolve()
    issues = []
    for page in site_pages(root):
        path = root / page
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        for reference in resource_references(soup):
            reference = reference.strip()
            if reference.startswith(('#', '%23')):
                continue
            url = urlsplit(reference)
            if url.scheme or url.netloc:
                continue
            resource_path = unquote(url.path)
            if not resource_path:
                continue
            target = (root / resource_path.lstrip('/') if resource_path.startswith('/')
                      else path.parent / resource_path).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                issues.append(f'{page}: missing local resource: {reference}')
    if issues:
        print('\n'.join(sorted(set(issues))))
        return 1
    print('Local script, media-source and CSS references exist')
    return 0


if __name__ == '__main__':
    sys.exit(audit_assets())
