#!/usr/bin/env python3
"""Structural prerequisites for every present and future public page."""
import json
import re
import sys
from collections import defaultdict
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from site_files import ROOT, indexing_issues, page_is_indexable, page_url_path, site_pages


def audit_page(html, page):
    soup = BeautifulSoup(html, 'html.parser')
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    require(soup.html and soup.html.get('lang') in ('en', 'it'), 'html needs en/it lang')
    require(bool(soup.head) and bool(soup.body), 'head and body required')
    if not soup.head or not soup.body:
        return errors
    require(len(soup.head.find_all('title')) == 1, 'exactly one head title required')
    require(soup.head.find('link', rel='icon') is not None, 'local favicon required')
    for name in ['description', 'viewport', 'theme-color']:
        metas = soup.head.find_all('meta', attrs={'name': name})
        require(len(metas) == 1 and bool(metas[0].get('content', '').strip()), f'exactly one nonempty {name} meta required')
    viewport = soup.head.find('meta', attrs={'name': 'viewport'})
    if viewport:
        require(not re.search(r'user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?:[,.]|$)', viewport.get('content', '')), 'do not disable zoom')
    csp = soup.find_all('meta', attrs={'http-equiv': re.compile('^Content-Security-Policy$', re.I)})
    require(len(csp) == 1 and bool(csp[0].get('content')) and csp[0].find_parent('head') is not None, 'exactly one CSP meta required')
    if len(csp) == 1 and csp[0].get('content'):
        directives = {parts[0]: set(parts[1:]) for directive in csp[0]['content'].split(';')
                      if (parts := directive.split())}
        required_tracking = {
            'script-src': {'https://www.googletagmanager.com'},
            'img-src': {'https://www.facebook.com', 'https://connect.facebook.net',
                'https://*.google-analytics.com', 'https://www.googletagmanager.com'},
            'form-action': {'https://www.facebook.com/tr/'},
            'connect-src': {'https://www.facebook.com', 'https://connect.facebook.net',
                'https://dv-c3e594c6d429469e90b54478358619c3.ecs.us-east-1.on.aws',
                'https://bded8a3c6ae-1-1053047382554.us-central1.run.app',
                'https://*.google-analytics.com', 'https://*.analytics.google.com',
                'https://www.googletagmanager.com'},
        }
        for directive, origins in required_tracking.items():
            missing = origins - directives.get(directive, set())
            require(not missing, f'CSP {directive} missing verified tracking sources: {", ".join(sorted(missing))}')
    canonicals = soup.find_all('link', rel='canonical')
    policy_errors = indexing_issues(page, soup)
    errors.extend(policy_errors)
    # Invalid noindex never grants exemptions from the normal page contract.
    noindex = not policy_errors and not page_is_indexable(page, soup)
    require(len(canonicals) <= 1 and (noindex or len(canonicals) == 1)
            and all(link.find_parent('head') is not None for link in canonicals), 'single canonical or intentional noindex required')
    if canonicals:
        expected = page_url_path(page)
        require(canonicals[0].get('href') == 'https://milanosensualcongress.com' + expected, 'canonical must match the clean page URL')
    require(len(soup.find_all('main')) == 1, 'exactly one main landmark required')
    require(len(soup.find_all('h1')) == 1, 'exactly one H1 required')
    require(len(soup.find_all('script', type='speculationrules')) == 1, 'one speculation-rules block required')
    for asset in ['site-analytics.js', 'prefetch-fallback.js']:
        require(len(soup.find_all('script', src=re.compile(r'^/js/' + re.escape(asset) + r'\?v='))) == 1, 'one shared ' + asset + ' loader required')
    require('function initMetaPixel' not in html, 'legacy inline Meta Pixel initializer is forbidden')
    for image in soup.find_all('img'):
        require(all(str(image.get(a, '')).isdigit() and int(image[a]) > 0 for a in ['width', 'height']), 'image missing dimensions: ' + image.get('src', ''))
    for control in soup.select('[aria-controls]'):
        for target in control['aria-controls'].split():
            require(soup.find(id=target) is not None, 'aria-controls points to a missing element: ' + target)
    for node in soup.find_all(['script', 'link']):
        url = node.get('src', '') if node.name == 'script' else node.get('href', '') if set(node.get('rel', [])) & {'stylesheet', 'preload'} else ''
        require(not url.startswith(('http:', 'https:', '//')), 'static script/styles must be self-hosted: ' + url)
    for url in re.findall(r'''url\(\s*['"]?((?:https?:)?//[^)'"\s]+)''', html):
        errors.append('CSS media/fonts must be self-hosted: ' + url)
    if not noindex:
        blocks = soup.find_all('script', type='application/ld+json')
        require(len(blocks) == 1 and blocks[0].find_parent('head') is not None, 'one unified JSON-LD graph in head required')
        if len(blocks) == 1:
            try:
                data = json.loads(blocks[0].string or blocks[0].get_text())
                require(isinstance(data.get('@graph'), list), 'JSON-LD needs @graph')
            except (ValueError, AttributeError):
                errors.append('invalid JSON-LD graph')
        if page not in ['index.html', 'it/index.html']:
            trail = soup.find('nav', attrs={'aria-label': re.compile('breadcrumb', re.I)})
            require(trail is not None and trail.has_attr('hidden') and 'display:none!important' in trail.get('style', '').replace(' ', ''), 'subpage needs the hidden breadcrumb trail')
        for lang in ['en', 'it', 'x-default']:
            require(len(soup.head.find_all('link', hreflang=lang)) == 1, 'one hreflang ' + lang + ' required')
    for node in soup.body.find_all(attrs={'itemprop': re.compile(r'^(author|datePublished|dateModified)$')}):
        errors.append('article editorial metadata must stay in the head: ' + node.get('itemprop'))
    return errors


def main():
    errors = []
    versions = defaultdict(set)
    for page in site_pages():
        html = (ROOT / page).read_text()
        errors.extend(f'{page}: {error}' for error in audit_page(html, page))
        for src, version in re.findall(r'(?:src|href)="(/(?:css|js|vendor)/[^"?]+)\?v=([^"&]+)', html):
            versions[src].add(version)
    for src, used in versions.items():
        if len(used) > 1:
            errors.append(f'{src}: inconsistent cache versions: {sorted(used)}')
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'{len(site_pages())} page contracts passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
