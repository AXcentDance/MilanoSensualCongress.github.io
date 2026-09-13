#!/usr/bin/env python3
"""Catch contradictory copies of the same congress entity without rewriting copy."""
from pathlib import Path

from event_facts import EVENT_ID, ORGANIZATION_ID, core_event, core_organization, definitions, entities, load_current_facts
from generation_support import GenerationError, run_generator
from site_files import classified_pages

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    facts = load_current_facts(root)
    errors = []
    count = 0
    shared = {}
    for page, soup, _indexable in classified_pages(root):
        matches = definitions(soup, page, EVENT_ID)
        if len(matches) > 1:
            errors.append(f'{page}: multiple definitions of the global congress entity')
        for event in matches:
            count += 1
            try:
                actual = core_event(event, page)
                for field, expected in facts['core'].items():
                    if actual[field] != expected:
                        errors.append(f'{page}: congress {field} is {actual[field]!r}; index.html has {expected!r}')
                # Other offers and subevents can legitimately have different destinations.
                offer = event.get('offers')
                if isinstance(offer, dict):
                    if offer.get('url') != facts['ticket_url']:
                        errors.append(f'{page}: global congress ticket URL disagrees with index.html')
                # One congress admission cannot become the price of an upgrade
                # on another page. addOn offers keep their own amounts/currencies.
                for field in ('@id', '@type', 'price', 'priceCurrency', 'availability', 'validFrom', 'validThrough'):
                    expected = facts['event']['offers'].get(field)
                    if expected is not None and (not isinstance(offer, dict) or offer.get(field) != expected):
                        errors.append(f'{page}: congress admission {field} disagrees with index.html')
                for field in ('url', 'mainEntityOfPage'):
                    expected = facts['event'].get(field)
                    if expected is not None and event.get(field) != expected:
                        errors.append(f'{page}: congress {field} disagrees with index.html')
            except GenerationError as error:
                errors.append(str(error))
        for organization in definitions(soup, page, ORGANIZATION_ID):
            for field, value in core_organization(organization).items():
                if value != facts['organization'].get(field):
                    errors.append(f'{page}: organization {field} disagrees with index.html')
        # Translations may change names/descriptions. Identifying URLs, contact
        # facts and an occurrence's teaching language must still agree by ID.
        for node in entities(soup, page):
            entity_id = node.get('@id')
            if not entity_id or set(node) == {'@id'}:
                continue
            for field in ('sameAs', 'telephone', 'email', 'availableLanguage',
                          'price', 'priceCurrency', 'validFrom', 'validThrough', 'availabilityStarts', 'availability'):
                if field not in node:
                    continue
                value = node[field]
                if isinstance(value, (str, list)):
                    value = sorted(value if isinstance(value, list) else [value])
                key = (entity_id, field)
                if key in shared and shared[key][0] != value:
                    errors.append(f'{page}: {entity_id} {field} disagrees with {shared[key][1]}')
                shared.setdefault(key, (value, page))
            node_types = node.get('@type', [])
            node_types = node_types if isinstance(node_types, list) else [node_types]
            if entity_id.startswith('https://milanosensualcongress.com/artists#'):
                key = (entity_id, 'artist identity type')
                value = sorted(set(node_types) & {'Person', 'PerformingGroup'})
                if key in shared and shared[key][0] != value:
                    errors.append(f'{page}: artist identity type disagrees with {shared[key][1]}')
                shared.setdefault(key, (value, page))
            if 'CourseInstance' in node_types:
                for field in ('startDate', 'endDate', 'inLanguage', 'courseMode', 'location', 'superEvent'):
                    key = (entity_id, field)
                    value = node.get(field)
                    if key in shared and shared[key][0] != value:
                        errors.append(f'{page}: CourseInstance {field} disagrees with {shared[key][1]}')
                    shared.setdefault(key, (value, page))
    if errors:
        raise GenerationError('\n'.join(errors))
    print(f'OK: {count} shared congress entities agree with homepage facts; bilingual statistics agree')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-copy', action='store_true',
                        help='report visible passages affected by changed source facts; never rewrite them')
    parser.add_argument('--base', default='HEAD', help='commit before the fact changes (default: HEAD)')
    args = parser.parse_args()
    if args.review_copy:
        from fact_copy_review import review_copy
        raise SystemExit(run_generator(lambda: review_copy(ROOT, args.base)))
    raise SystemExit(run_generator(check))
