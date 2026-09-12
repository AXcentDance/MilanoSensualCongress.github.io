#!/usr/bin/env python3
"""Master site gate: runs every checker and fails (exit 1) on any violation.

Runs the single-purpose checkers and checks their exit codes and success markers.
Page requirements belong to check_page_contract.py; image alt/source requirements
belong to check_image_seo.py. This orchestrator adds cross-page title/description
uniqueness and sitemap validity/coverage checks.

Run from the repo root:  python3 scripts/run_all_checks.py
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from site_files import site_pages

FAILURES = []

# ---- absorbed checkers: (command args, success marker in stdout) ----
CHECKERS = [
    (['scripts/check_page_contract.py'], 'page contracts passed'),
    (['scripts/check_image_seo.py'], 'image attributes passed'),
    (['scripts/check_html_syntax.py'], 'No syntax errors'),
    (['scripts/audit_links.py'], 'No broken relative links'),
    (['scripts/audit_schema.py'], 'valid JSON'),
    (['scripts/audit_hreflang.py'], 'perfectly reciprocal'),
    (['scripts/audit_og.py'], 'consistent and valid'),
    (['scripts/audit_headings.py'], 'Heading structure audit passed!'),
    (['scripts/check_orphans.py'], 'no orphan pages'),
    (['scripts/update_price.py', '--check'], 'price facts consistent'),
    (['scripts/generate_md_twins.py', '--check'], 'md twins up to date'),
    (['scripts/inline_critical_css.py', '--check'], 'critical css fresh'),
]


def pages():
    return site_pages()


def run_absorbed_checkers():
    for args, marker in CHECKERS:
        proc = subprocess.run([sys.executable] + args, capture_output=True, text=True)
        if proc.returncode != 0 or marker not in proc.stdout:
            FAILURES.append(f'{" ".join(args)}: failed (exit {proc.returncode})')
            print((proc.stdout + proc.stderr)[-6000:])
        else:
            for line in (proc.stdout + proc.stderr).splitlines():
                if 'warning' in line.lower() or line.lstrip().startswith('!'):
                    print(line)


def check_metadata_unique():
    seen = {'title': {}, 'meta description': {}}
    for page in pages():
        with open(page) as source:
            head = BeautifulSoup(source.read(), 'html.parser').head
        # Presence/cardinality are owned by the page-contract checker.
        if head is None:
            continue
        title = head.find('title')
        description = head.find('meta', attrs={'name': 'description'})
        values = {
            'title': title.get_text().strip() if title is not None else None,
            'meta description': ' '.join(description.get('content', '').split()) if description is not None else None,
        }
        for name, value in values.items():
            if value is None:
                continue
            if value in seen[name]:
                FAILURES.append(f'duplicate {name} in {page} and {seen[name][value]}: "{value[:60]}"')
            seen[name][value] = page


def check_sitemap():
    try:
        tree = ET.parse('sitemap.xml')
    except ET.ParseError as e:
        FAILURES.append(f'sitemap.xml: XML parse error {e}')
        return
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locs = {u.findtext('sm:loc', namespaces=ns) for u in tree.getroot().findall('sm:url', ns)}
    # every indexable page must be in the sitemap
    for page in pages():
        html = open(page).read()
        if 'noindex' in html:
            continue
        path = '/' + page[:-5]
        if path.endswith('/index'):
            path = path[:-5]
        url = 'https://milanosensualcongress.com' + path
        if url not in locs and url.rstrip('/') not in locs:
            FAILURES.append(f'sitemap.xml: missing indexable page {url}')


def main():
    run_absorbed_checkers()
    check_metadata_unique()
    check_sitemap()
    if FAILURES:
        print(f'\nFAILED: {len(FAILURES)} violation(s)')
        for f in FAILURES:
            print(' -', f)
        sys.exit(1)
    print('OK: all site checks passed')


if __name__ == '__main__':
    main()
