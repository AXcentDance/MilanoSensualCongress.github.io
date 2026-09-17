#!/usr/bin/env python3
"""Single switch for the canonical Full Pass offer facts.

Every page that embeds a DanceEvent Offer (root pages, it/, news/, it/news/)
must agree on the current Full Pass price and its validThrough deadline.
The canonical values live at the top of this script; the master gate runs
``--check`` so any page that drifts fails the local quality gate.

Usage:
    python3 scripts/update_price.py --check
        Verify every page. Prints "price facts consistent" and exits 0 when
        everything agrees; otherwise lists each divergent page/field and
        exits 1.

    python3 scripts/update_price.py --set PRICE VALID_THROUGH [VALID_FROM]
        Supply VALID_FROM when changing to a new price tier.
        Rewrites, in every JSON-LD block: the Full Pass offer price, the
        outer/aggregate price fields, and every UnitPriceSpecification named
        like "Current Full Pass" / "Full Pass attuale". Also updates the
        canonical constants below so a subsequent --check passes.

What counts as a Full Pass node:
  * any Offer or UnitPriceSpecification whose name matches
    "Current Full Pass" / "Full Pass attuale" (case-insensitive);
  * any *unnamed* EUR Offer that carries a "price" key (the event's outer
    offer -- e.g. program.html, index.html);
  * the highPrice of an AggregateOffer whose nested offers include a named
    Full Pass offer (e.g. tickets.html).
Named non-Full-Pass offers (Masterclass Upgrade, Jack & Jill, "Next Full
Pass Tier") are left untouched.
"""
from site_files import site_pages
import json
import os
import re
import sys
from datetime import datetime, timezone

from bs4 import BeautifulSoup

# ---- canonical Full Pass facts (the single switch) ----
FULL_PASS_PRICE = "130.00"
FULL_PASS_VALID_THROUGH = "2026-10-15T23:59:59+02:00"
FULL_PASS_VALID_FROM = "2026-08-01T00:00:00+02:00"
NEXT_FULL_PASS_PRICE = "135.00"
NEXT_FULL_PASS_VALID_FROM = "2026-10-16T00:00:00+02:00"
# The next tier's end date has not been announced. Do not invent one.
NEXT_FULL_PASS_ID = "https://milanosensualcongress.com/tickets#full-pass-next"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FULL_PASS_NAME_RE = re.compile(r'^(current full pass|full pass attuale)$', re.I)
LDJSON_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def pages():
    os.chdir(REPO_ROOT)
    return site_pages()


def is_full_pass_name(name):
    return isinstance(name, str) and FULL_PASS_NAME_RE.match(name.strip())


def visit(node, price, valid_through, problems, page, apply_changes, valid_from=None):
    """Walk a JSON-LD structure; check or rewrite Full Pass facts.

    Returns True if the structure was modified (only in apply mode).
    """
    changed = False

    def handle_field(obj, key, want, label):
        nonlocal changed
        have = obj.get(key)
        if have == want:
            return
        if apply_changes:
            obj[key] = want
            changed = True
        else:
            problems.append(f'{page}: {label} {key}={have!r} (want {want!r})')

    if isinstance(node, dict):
        t = node.get('@type')
        types = t if isinstance(t, list) else [t]
        name = node.get('name')

        if 'Offer' in types:
            if is_full_pass_name(name):
                handle_field(node, 'price', price, f'offer "{name}"')
                if valid_from is not None:
                    handle_field(node, 'validFrom', valid_from, f'offer "{name}"')
                if 'validThrough' in node or not apply_changes:
                    handle_field(node, 'validThrough', valid_through, f'offer "{name}"')
            elif name is None and 'price' in node and node.get('priceCurrency') == 'EUR':
                handle_field(node, 'price', price, 'outer offer')
                if valid_from is not None:
                    handle_field(node, 'validFrom', valid_from, 'outer offer')
                if 'validThrough' in node:
                    handle_field(node, 'validThrough', valid_through, 'outer offer')

        elif 'UnitPriceSpecification' in types and is_full_pass_name(name):
            handle_field(node, 'price', price, f'priceSpecification "{name}"')
            handle_field(node, 'validThrough', valid_through, f'priceSpecification "{name}"')

        elif 'AggregateOffer' in types:
            nested = node.get('offers')
            nested = nested if isinstance(nested, list) else []
            if any(isinstance(o, dict) and is_full_pass_name(o.get('name')) for o in nested):
                if 'highPrice' in node:
                    handle_field(node, 'highPrice', price, 'aggregate offer')

        for value in node.values():
            if visit(value, price, valid_through, problems, page, apply_changes, valid_from):
                changed = True

    elif isinstance(node, list):
        for item in node:
            if visit(item, price, valid_through, problems, page, apply_changes, valid_from):
                changed = True

    return changed


def process_page(page, price, valid_through, problems, apply_changes, valid_from=None):
    with open(page, encoding='utf-8') as f:
        html = f.read()
    out = []
    last = 0
    modified = False
    for m in LDJSON_RE.finditer(html):
        out.append(html[last:m.start()])
        open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # audit_schema.py owns JSON validity; leave the block untouched.
            out.append(m.group(0))
            last = m.end()
            continue
        if visit(data, price, valid_through, problems, page, apply_changes, valid_from):
            body = '\n' + json.dumps(data, ensure_ascii=False, indent=2) + '\n'
            modified = True
        out.append(open_tag + body + close_tag)
        last = m.end()
    out.append(html[last:])
    if apply_changes and modified:
        with open(page, 'w', encoding='utf-8') as f:
            f.write(''.join(out))
    return modified


def rewrite_own_constants(price, valid_through, valid_from):
    path = os.path.abspath(__file__)
    with open(path, encoding='utf-8') as f:
        src = f.read()
    src = re.sub(r'^FULL_PASS_PRICE = ".*?"$',
                 f'FULL_PASS_PRICE = "{price}"', src, count=1, flags=re.M)
    src = re.sub(r'^FULL_PASS_VALID_THROUGH = ".*?"$',
                 f'FULL_PASS_VALID_THROUGH = "{valid_through}"', src, count=1, flags=re.M)
    src = re.sub(r'^FULL_PASS_VALID_FROM = ".*?"$',
                 f'FULL_PASS_VALID_FROM = "{valid_from}"', src, count=1, flags=re.M)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(src)


def normalize_price(raw):
    try:
        return f'{float(raw):.2f}'
    except ValueError:
        sys.exit(f'invalid price: {raw!r}')


def check_deadline(valid_through, now=None):
    """Stop a local build/release from silently retaining an expired price.

    This does not schedule a deployment or change the live static website.
    """
    try:
        deadline = datetime.fromisoformat(valid_through.replace('Z', '+00:00'))
        if deadline.tzinfo is None:
            return ['Full Pass deadline must include a timezone offset']
    except (ValueError, AttributeError):
        return [f'invalid Full Pass deadline: {valid_through!r}']
    if (now or datetime.now(timezone.utc)) > deadline:
        return [f'Full Pass offer expired at {valid_through}; update the current '
                'price, visible copy and countdowns before release']
    return []


def check_next_tier(page):
    """The announced tier stays separate from the currently purchasable offer."""
    if page not in ('tickets.html', 'it/tickets.html'):
        return []
    with open(page, encoding='utf-8') as source:
        soup = BeautifulSoup(source.read(), 'html.parser')
    problems = []
    from schema_contract import nodes
    upcoming = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            upcoming.extend(n for n in nodes(json.loads(script.string or ''))
                            if n.get('@id') == NEXT_FULL_PASS_ID and n.get('@type') == 'Offer')
        except json.JSONDecodeError:
            continue  # JSON validity belongs to audit_schema.py.
    if len(upcoming) != 1:
        problems.append(f'{page}: needs one announced next Full Pass offer')
    else:
        for field, expected in [('price', NEXT_FULL_PASS_PRICE), ('priceCurrency', 'EUR'),
                                ('validFrom', NEXT_FULL_PASS_VALID_FROM),
                                ('availabilityStarts', NEXT_FULL_PASS_VALID_FROM)]:
            if upcoming[0].get(field) != expected:
                problems.append(f'{page}: next Full Pass {field} disagrees with canonical facts')
    card = soup.select_one('#next-full-pass-tier')
    amount = card.select_one('[data-next-full-pass-price]') if card else None
    start = card.select_one('time[datetime]') if card else None
    if amount is None or amount.get('data-next-full-pass-price') != NEXT_FULL_PASS_PRICE \
            or amount.get_text(strip=True) != '€' + f'{float(NEXT_FULL_PASS_PRICE):g}':
        problems.append(f'{page}: visible next Full Pass price disagrees with canonical facts')
    if start is None or start.get('datetime') != NEXT_FULL_PASS_VALID_FROM:
        problems.append(f'{page}: visible next Full Pass start disagrees with canonical facts')
    return problems


def main(argv):
    if argv[:1] == ['--set']:
        if len(argv) not in (3, 4):
            sys.exit('usage: update_price.py --set PRICE VALID_THROUGH [VALID_FROM]')
        price = normalize_price(argv[1])
        valid_through = argv[2]
        if price != FULL_PASS_PRICE and len(argv) != 4:
            sys.exit('a new price tier needs its confirmed VALID_FROM timestamp')
        valid_from = argv[3] if len(argv) == 4 else FULL_PASS_VALID_FROM
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$', valid_through):
            sys.exit(f'invalid validThrough (need full ISO-8601 with offset): {valid_through!r}')
        try:
            start, end = (datetime.fromisoformat(value) for value in (valid_from, valid_through))
            if start.tzinfo is None or start > end:
                raise ValueError('start must have a timezone and precede the deadline')
        except ValueError as error:
            sys.exit(f'invalid price interval: {error}')
        touched = []
        for page in pages():
            if process_page(page, price, valid_through, [], apply_changes=True, valid_from=valid_from):
                touched.append(page)
        rewrite_own_constants(price, valid_through, valid_from)
        print(f'Updated {len(touched)} page(s) to price={price}, validThrough={valid_through}')
        for page in touched:
            print(' -', page)
        return 0

    if argv and argv != ['--check']:
        sys.exit('usage: update_price.py [--check | --set PRICE VALID_THROUGH [VALID_FROM]]')

    problems = check_deadline(FULL_PASS_VALID_THROUGH)
    for page in pages():
        process_page(page, FULL_PASS_PRICE, FULL_PASS_VALID_THROUGH, problems,
                     apply_changes=False, valid_from=FULL_PASS_VALID_FROM)
        problems.extend(check_next_tier(str(page)))
    if problems:
        print(f'FAILED: {len(problems)} price fact divergence(s) '
              f'(canonical: {FULL_PASS_PRICE} EUR until {FULL_PASS_VALID_THROUGH})')
        for p in problems:
            print(' -', p)
        return 1
    print(f'price facts consistent ({FULL_PASS_PRICE} EUR, valid through '
          f'{FULL_PASS_VALID_THROUGH})')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
