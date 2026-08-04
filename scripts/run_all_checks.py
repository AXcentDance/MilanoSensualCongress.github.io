#!/usr/bin/env python3
"""Master site gate: runs every checker and fails (exit 1) on any violation.

Absorbs the single-purpose audit scripts by matching their success markers,
and adds repo-wide invariant checks (CSP presence, speculation rules presence,
theme-color presence, sitemap validity/coverage, duplicate titles).

Run from the repo root:  python3 scripts/run_all_checks.py
"""
import glob
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

FAILURES = []

# ---- absorbed checkers: (script, success marker in stdout) ----
CHECKERS = [
    ('scripts/check_html_syntax.py', 'No syntax errors'),
    ('scripts/audit_links.py', 'No broken relative links'),
    ('scripts/audit_schema.py', 'valid JSON'),
    ('scripts/audit_hreflang.py', 'perfectly reciprocal'),
    ('scripts/audit_og.py', 'consistent and valid'),
]


def pages():
    return (glob.glob('*.html') + glob.glob('it/*.html')
            + glob.glob('news/*.html') + glob.glob('it/news/*.html'))


def run_absorbed_checkers():
    for script, marker in CHECKERS:
        proc = subprocess.run([sys.executable, script], capture_output=True, text=True)
        if marker not in proc.stdout:
            FAILURES.append(f'{script}: success marker "{marker}" not found')
            print(proc.stdout[-1500:])


def check_per_page_invariants():
    for page in pages():
        html = open(page).read()
        checks = {
            'CSP meta': 'http-equiv="Content-Security-Policy"' in html,
            'speculation rules': 'type="speculationrules"' in html,
            'theme-color': 'name="theme-color"' in html,
            'single canonical or noindex': (
                html.count('rel="canonical"') == 1 or 'noindex' in html),
        }
        for name, ok in checks.items():
            if not ok:
                FAILURES.append(f'{page}: missing {name}')
        # exactly one CSP meta
        if html.count('http-equiv="Content-Security-Policy"') > 1:
            FAILURES.append(f'{page}: more than one CSP meta')


def check_titles_unique():
    seen = {}
    for page in pages():
        m = re.search(r'<title>(.*?)</title>', open(page).read(), re.S)
        if not m:
            FAILURES.append(f'{page}: missing <title>')
            continue
        t = m.group(1).strip()
        if t in seen:
            FAILURES.append(f'duplicate title in {page} and {seen[t]}: "{t[:60]}"')
        seen[t] = page


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
    check_per_page_invariants()
    check_titles_unique()
    check_sitemap()
    if FAILURES:
        print(f'\nFAILED: {len(FAILURES)} violation(s)')
        for f in FAILURES:
            print(' -', f)
        sys.exit(1)
    print('OK: all site checks passed')


if __name__ == '__main__':
    main()
