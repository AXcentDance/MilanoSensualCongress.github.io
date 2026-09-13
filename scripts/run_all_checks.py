#!/usr/bin/env python3
"""Master site gate: runs every checker and fails (exit 1) on any violation.

Runs the single-purpose checkers and checks their exit codes.
Page requirements belong to check_page_contract.py; image alt/source requirements
belong to check_image_seo.py. This orchestrator adds cross-page title/description
uniqueness and sitemap validity/coverage checks.

Run from the repo root:  python3 scripts/run_all_checks.py
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from generation_support import GenerationError
from site_files import page_is_indexable, page_url_path, site_pages

FAILURES = []

# Single-purpose checkers return 0 for success, nonzero for failure. The label is
# for readers; changing human-readable checker output cannot change the result.
CHECKERS = [
    (['scripts/check_release_files.py'], 'Publication file protections'),
    (['scripts/check_page_contract.py'], 'Page contracts'),
    (['scripts/check_image_seo.py'], 'Image semantics and sources'),
    (['scripts/check_html_syntax.py'], 'HTML syntax'),
    (['scripts/audit_links.py'], 'Internal links'),
    (['scripts/audit_assets.py'], 'Local resource integrity'),
    (['scripts/audit_schema.py'], 'Structured data'),
    (['scripts/check_event_facts.py'], 'Shared congress facts'),
    (['scripts/audit_hreflang.py'], 'Language relationships'),
    (['scripts/audit_og.py'], 'Social metadata'),
    (['scripts/audit_headings.py'], 'Heading structure'),
    (['scripts/check_orphans.py'], 'Page reachability'),
    (['scripts/update_price.py', '--check'], 'Price facts'),
    (['scripts/generate_md_twins.py', '--check'], 'Markdown freshness'),
    (['scripts/generate_rss.py', '--check'], 'RSS freshness'),
    (['scripts/generate_llms_text.py', '--check'], 'LLM export freshness'),
    (['scripts/generate_sitemap.py', '--check'], 'Sitemap freshness'),
    (['scripts/inline_critical_css.py', '--check'], 'Critical CSS freshness'),
]


def pages():
    return site_pages()


def run_absorbed_checkers():
    for args, label in CHECKERS:
        try:
            proc = subprocess.run([sys.executable] + args, capture_output=True, text=True)
        except OSError as error:
            FAILURES.append(f'{" ".join(args)}: could not run: {error}')
            continue
        if proc.returncode != 0:
            FAILURES.append(f'{" ".join(args)}: failed (exit {proc.returncode})')
            print(proc.stdout + proc.stderr)
        else:
            print(f'PASS: {label}')
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
    except (ET.ParseError, OSError) as e:
        FAILURES.append(f'sitemap.xml: XML parse error {e}')
        return
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locs = {u.findtext('sm:loc', namespaces=ns) for u in tree.getroot().findall('sm:url', ns)}
    expected = set()
    # Require complete coverage and reject stale/nonindexed/tooling entries.
    for page in pages():
        with open(page, encoding='utf-8') as source:
            soup = BeautifulSoup(source.read(), 'html.parser')
        try:
            indexable = page_is_indexable(page, soup)
        except GenerationError as error:
            FAILURES.append(f'sitemap.xml: {error}')
            continue
        if not indexable:
            continue
        url = 'https://milanosensualcongress.com' + page_url_path(page)
        expected.add(url.rstrip('/'))
        if url not in locs and url.rstrip('/') not in locs:
            FAILURES.append(f'sitemap.xml: missing indexable page {url}')
    for url in sorted(locs, key=str):
        if not url or url.rstrip('/') not in expected:
            FAILURES.append(f'sitemap.xml: URL is not an indexable public page: {url}')


def main():
    FAILURES.clear()
    run_absorbed_checkers()
    check_metadata_unique()
    check_sitemap()
    if FAILURES:
        print(f'\nFAILED: {len(FAILURES)} violation(s)')
        for f in FAILURES:
            print(' -', f)
        return 1
    print('OK: all site checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
