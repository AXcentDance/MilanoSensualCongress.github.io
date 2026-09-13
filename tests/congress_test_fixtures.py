"""Synthetic congress data for isolated generator tests; never production facts."""
import json
from pathlib import Path

from event_facts import EVENT_ID, ORGANIZATION_ID, core_event


def facts():
    event = {
        '@type': 'DanceEvent', '@id': EVENT_ID, 'name': 'Test Congress 2030',
        'startDate': '2030-06-01T18:00:00+02:00', 'endDate': '2030-06-03T23:00:00+02:00',
        'eventStatus': 'https://schema.org/EventScheduled',
        'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
        'location': {'name': 'Test Venue', 'address': {
            'streetAddress': 'Test Street 1', 'addressLocality': 'Test City',
            'postalCode': '12345', 'addressRegion': 'MI', 'addressCountry': 'IT'}},
        'organizer': {'@id': ORGANIZATION_ID},
        'offers': {'@type': 'Offer', 'url': 'https://example.com/test-tickets'},
    }
    return {'event': event, 'core': core_event(event, 'test fixture'),
            'organization': {'name': 'Test Organization', 'url': 'https://example.com'},
            'statistics': {'en': '2,000+ dancers · 4 days', 'it': '2.000+ ballerini · 4 giorni'},
            'ticket_url': event['offers']['url']}


def write_homepages(root, data=None):
    data = data or facts()
    for path, language in [('index.html', 'en'), ('it/index.html', 'it')]:
        target = Path(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        organization = {'@type': 'Organization', '@id': ORGANIZATION_ID, **data['organization']}
        graph = json.dumps({'@context': 'https://schema.org', '@graph': [data['event'], organization]})
        target.write_text(f'<html><head><title>Test Congress</title>'
                          f'<script type="application/ld+json">{graph}</script></head>'
                          f'<body><main><p id="congress-facts">{data["statistics"][language]}</p>'
                          '</main></body></html>', encoding='utf-8')
