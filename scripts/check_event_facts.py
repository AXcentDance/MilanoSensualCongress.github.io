#!/usr/bin/env python3
"""Catch contradictory copies of the same congress entity without rewriting copy."""
from pathlib import Path

from event_facts import EVENT_ID, ORGANIZATION_ID, core_event, core_organization, definitions, load_current_facts
from generation_support import GenerationError, run_generator
from site_files import classified_pages

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    facts = load_current_facts(root)
    errors = []
    count = 0
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
            except GenerationError as error:
                errors.append(str(error))
        for organization in definitions(soup, page, ORGANIZATION_ID):
            for field, value in core_organization(organization).items():
                if value != facts['organization'].get(field):
                    errors.append(f'{page}: organization {field} disagrees with index.html')
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
