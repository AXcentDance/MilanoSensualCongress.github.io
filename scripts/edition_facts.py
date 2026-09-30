"""Confirmed next-edition facts, separate from the retained 2026 sales record.

The public JSON file also supplies promotional materials. Calendar dates must
never acquire invented hours, prices or performers during site generation.
"""
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from event_facts import ADDRESS_FIELDS, ORGANIZATION_ID, SITE, definitions, entities, required
from generation_support import GenerationError, read_page

EDITION_PATH = Path('data/editions/2027.json')
EDITION_EVENT_ID = SITE + '/#event-2027'


def load_announced_edition(root):
    """Load and validate the announcement; old single-edition fixtures remain valid."""
    root = Path(root)
    source = root / EDITION_PATH
    if not source.exists():
        for page in ('index.html', 'it/index.html'):
            if (root / page).exists() and any(node.get('@id') == EDITION_EVENT_ID
                                            for node in entities(read_page(root / page), page)):
                raise GenerationError(f'{EDITION_PATH}: missing source for the announced edition')
        return None
    try:
        data = json.loads(source.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise GenerationError(f'{EDITION_PATH}: cannot read edition facts: {error}') from error
    if not isinstance(data, dict):
        raise GenerationError(f'{EDITION_PATH}: edition facts must be an object')
    for field, expected in [('edition', 2027), ('eventId', EDITION_EVENT_ID),
                            ('timezone', 'Europe/Rome'), ('datePrecision', 'day')]:
        if data.get(field) != expected:
            raise GenerationError(f'{EDITION_PATH}: {field} must be {expected!r}')
    required(data, 'name', EDITION_PATH)
    try:
        dates = []
        for field in ('startDate', 'endDate'):
            value = required(data, field, EDITION_PATH)
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError(f'{field} must be a calendar date without an invented time')
            dates.append(date.fromisoformat(value))
        if dates[1] < dates[0] or any(value.year != data['edition'] for value in dates):
            raise ValueError('dates must be ordered within the announced edition year')
    except ValueError as error:
        raise GenerationError(f'{EDITION_PATH}: invalid edition dates: {error}') from error
    for field in ('name', *ADDRESS_FIELDS):
        required(data.get('venue'), field, EDITION_PATH)
    status = data.get('status', {})
    for field, expected in [('dates', 'confirmed'), ('venue', 'confirmed'),
                            ('times', 'unannounced'), ('tickets', 'unannounced'), ('lineup', 'preview')]:
        if not isinstance(status, dict) or status.get(field) != expected:
            raise GenerationError(f'{EDITION_PATH}: status.{field} must be {expected!r}')
    if 'earlyBird' in data:
        early_bird = data['earlyBird']
        if not isinstance(early_bird, dict):
            raise GenerationError(f'{EDITION_PATH}: earlyBird must be an object')
        for field, expected in [('datePrecision', 'day'), ('timezone', 'Europe/Rome')]:
            if early_bird.get(field) != expected:
                raise GenerationError(f'{EDITION_PATH}: earlyBird.{field} must be {expected!r}')
        try:
            ends_on = early_bird.get('endsOn')
            if not isinstance(ends_on, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', ends_on):
                raise ValueError('endsOn must be a calendar date')
            following_day = date.fromisoformat(ends_on) + timedelta(days=1)
            deadline = datetime.combine(following_day, time(), ZoneInfo('Europe/Rome')).isoformat()
        except (ValueError, OverflowError) as error:
            raise GenerationError(f'{EDITION_PATH}: invalid earlyBird date: {error}') from error
        if early_bird.get('countdownDeadline') != deadline:
            raise GenerationError(f'{EDITION_PATH}: earlyBird.countdownDeadline must be '
                                  f'the following midnight in Europe/Rome ({deadline})')
    return data


def schema_event(edition, language='en'):
    """The announcement intentionally has no admission or lineup relationship."""
    venue = edition['venue']
    description = (f"{edition['name']} torna al {venue['name']}. Date e sede confermate; "
                   'orari, biglietti e lineup saranno annunciati.' if language == 'it' else
                   f"{edition['name']} returns to {venue['name']}. Dates and venue are confirmed; "
                   'times, tickets and lineup will be announced.')
    return {
        '@type': 'DanceEvent', '@id': edition['eventId'], 'name': edition['name'],
        'startDate': edition['startDate'], 'endDate': edition['endDate'],
        'eventStatus': 'https://schema.org/EventScheduled',
        'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
        'location': {'@type': 'Place', 'name': venue['name'],
                     'address': {'@type': 'PostalAddress', **{field: venue[field] for field in ADDRESS_FIELDS}}},
        'organizer': {'@id': ORGANIZATION_ID},
        'url': SITE + '/', 'mainEntityOfPage': SITE + '/',
        'image': [SITE + '/images/milano-sensual-congress-official-logo-preview.webp'],
        'description': description,
    }


def check_edition_page(page, soup, edition):
    """Compare every announcement copy; homepages must expose its real dates."""
    errors = []
    matches = definitions(soup, page, edition['eventId'])
    homepage = page in ('index.html', 'it/index.html')
    if len(matches) > 1 or (homepage and len(matches) != 1):
        errors.append(f'{page}: expected one announced-edition DanceEvent definition')
    expected = schema_event(edition)
    for event in matches:
        for field in ('@type', 'name', 'startDate', 'endDate', 'eventStatus', 'eventAttendanceMode',
                      'location', 'organizer', 'url', 'mainEntityOfPage'):
            if event.get(field) != expected[field]:
                errors.append(f'{page}: announced edition {field} disagrees with {EDITION_PATH}')
        for field in ('offers', 'performer', 'subEvent'):
            if field in event:
                errors.append(f'{page}: announced edition must not imply confirmed {field}')
    if not homepage:
        return errors
    canonical = SITE + ('/it/' if page.startswith('it/') else '/')
    pages = definitions(soup, page, canonical + '#webpage')
    if len(pages) != 1 or pages[0].get('mainEntity') != {'@id': edition['eventId']}:
        errors.append(f'{page}: homepage mainEntity must identify the announced edition')
    paragraphs = soup.select('main #edition-facts')
    if len(paragraphs) != 1:
        return errors + [f'{page}: expected one visible #edition-facts announcement in main']
    paragraph = paragraphs[0]
    if any(parent.has_attr('hidden') or parent.get('aria-hidden') == 'true'
           or re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', parent.get('style', ''), re.I)
           for parent in [paragraph, *paragraph.parents] if hasattr(parent, 'attrs')):
        errors.append(f'{page}: #edition-facts must remain visible')
    if {node.get('datetime') for node in paragraph.select('time[datetime]')} != {
            edition['startDate'], edition['endDate']}:
        errors.append(f'{page}: visible edition dates disagree with {EDITION_PATH}')
    text = paragraph.get_text(' ', strip=True)
    if edition['venue']['name'] not in text or str(edition['edition']) not in text:
        errors.append(f'{page}: visible edition venue/year disagree with {EDITION_PATH}')
    if 'earlyBird' in edition:
        early_bird = edition['earlyBird']
        timers = soup.select('main [data-early-bird-countdown]')
        if len(timers) != 1:
            errors.append(f'{page}: expected one early-bird countdown in main')
        else:
            if timers[0].get('data-deadline') != early_bird['countdownDeadline']:
                errors.append(f'{page}: early-bird countdown deadline disagrees with {EDITION_PATH}')
            dates = timers[0].parent.select('[data-countdown-status] time[datetime]')
            if len(dates) != 1 or dates[0].get('datetime') != early_bird['endsOn']:
                errors.append(f'{page}: early-bird status date disagrees with {EDITION_PATH}')
    return errors


def edition_date_range(edition):
    start, end = (date.fromisoformat(edition[field]) for field in ('startDate', 'endDate'))
    if start.year == end.year and start.month == end.month:
        return f'{start:%B} {start.day}-{end.day}, {start.year}'
    return f'{start:%B} {start.day}, {start.year} – {end:%B} {end.day}, {end.year}'


def edition_location(edition):
    venue = edition['venue']
    country = {'IT': 'Italy'}.get(venue['addressCountry'], venue['addressCountry'])
    return f"{venue['name']}, {venue['addressLocality']} ({venue['addressRegion']}), {country}"
