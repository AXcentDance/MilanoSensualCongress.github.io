"""Read shared congress facts from their existing, visitor-visible sources.

The English homepage owns language-independent event facts; the Italian
homepage owns its translated statistics. Price amounts/deadlines remain owned
and checked by update_price.py. Do not keep another edition-specific template.
"""
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from generation_support import GenerationError, read_page
from iso_dates import iso_datetime

SITE = 'https://milanosensualcongress.com'
EVENT_ID = SITE + '/#event'
ORGANIZATION_ID = SITE + '/#organization'
EVENT_FIELDS = ('name', 'startDate', 'endDate', 'eventStatus', 'eventAttendanceMode')
ADDRESS_FIELDS = ('streetAddress', 'addressLocality', 'postalCode', 'addressRegion', 'addressCountry')


def entities(soup, source):
    """Yield graph nodes, including embedded entities, but never parse body code."""
    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    if soup.head:
        for script in soup.head.find_all('script', attrs={'type': 'application/ld+json'}):
            try:
                yield from walk(json.loads(script.get_text()))
            except (ValueError, TypeError) as error:
                raise GenerationError(f'{source}: invalid JSON-LD: {error}') from error


def definitions(soup, source, entity_id):
    return [node for node in entities(soup, source)
            if node.get('@id') == entity_id and set(node) != {'@id'}]


def one_definition(soup, source, entity_id):
    matches = definitions(soup, source, entity_id)
    if len(matches) != 1:
        raise GenerationError(f'{source}: expected one definition of {entity_id}; found {len(matches)}')
    return matches[0]


def required(value, field, source):
    result = value.get(field) if isinstance(value, dict) else None
    if not isinstance(result, str) or not result.strip():
        raise GenerationError(f'{source}: missing or invalid {field}')
    return result.strip()


def core_event(event, source):
    types = event.get('@type', [])
    if 'DanceEvent' not in (types if isinstance(types, list) else [types]):
        raise GenerationError(f'{source}: global congress definition must have type DanceEvent')
    result = {field: required(event, field, source) for field in EVENT_FIELDS}
    try:
        start, end = (iso_datetime(result[field]) for field in ('startDate', 'endDate'))
        if end < start:
            raise ValueError('start/end must include timezone offsets and end must follow start')
    except ValueError as error:
        raise GenerationError(f'{source}: invalid congress dates: {error}') from error
    # Comparisons use instants, not offset spellings. The source event is untouched.
    result.update(startDate=start, endDate=end)
    location = event.get('location', {})
    result['location.name'] = required(location, 'name', source)
    for field in ADDRESS_FIELDS:
        result['location.address.' + field] = required(location.get('address'), field, source)
    result['organizer.@id'] = required(event.get('organizer'), '@id', source)
    return result


def core_organization(entity):
    """Compare present identifying facts; minimal references can omit details."""
    result = {key: entity[key] for key in ('name', 'logo', 'foundingDate') if key in entity}
    if isinstance(entity.get('url'), str):
        result['url'] = entity['url'].rstrip('/')
    address = entity.get('address', {})
    if isinstance(address, dict):
        for field in ADDRESS_FIELDS:
            if field in address:
                result['address.' + field] = address[field]
    for key in ('sameAs', 'founder', 'contactPoint'):
        if key not in entity:
            continue
        values = entity[key] if isinstance(entity[key], list) else [entity[key]]
        if key == 'founder':
            values = [{k: v[k] for k in ('@id', 'name', 'sameAs') if k in v}
                      if isinstance(v, dict) else v for v in values]
        elif key == 'contactPoint':
            values = [{k: v[k] for k in ('telephone', 'url', 'email') if k in v}
                      if isinstance(v, dict) else v for v in values]
        result[key] = sorted(json.dumps(value, sort_keys=True, ensure_ascii=False) for value in values)
    return result


def statistics(soup, source):
    matches = soup.select('main #congress-facts')
    if len(matches) != 1 or not matches[0].get_text(' ', strip=True):
        raise GenerationError(f'{source}: expected one nonempty visible #congress-facts summary in main')
    node = matches[0]
    if any(parent.has_attr('hidden') or parent.get('aria-hidden') == 'true'
           for parent in [node, *node.parents] if hasattr(parent, 'attrs')):
        raise GenerationError(f'{source}: #congress-facts must remain visible')
    return node.get_text(' ', strip=True)


def load_current_facts(root):
    root = Path(root)
    home = read_page(root / 'index.html')
    italian = read_page(root / 'it/index.html')
    event = one_definition(home, 'index.html', EVENT_ID)
    core = core_event(event, 'index.html')
    translated = core_event(one_definition(italian, 'it/index.html', EVENT_ID), 'it/index.html')
    for field, value in core.items():
        if translated[field] != value:
            raise GenerationError(f'it/index.html: congress {field} disagrees with index.html')
    stats = {language: statistics(soup, source) for language, soup, source in [
        ('en', home, 'index.html'), ('it', italian, 'it/index.html')]}
    # Compare quantities without imposing a fixed audience size or number of facts.
    quantities = lambda text: [re.sub(r'[.,]', '', n) for n in re.findall(r'\d[\d.,]*\+?', text)]
    if quantities(stats['en']) != quantities(stats['it']):
        raise GenerationError('it/index.html: congress statistics quantities disagree with index.html')
    offer = event.get('offers')
    ticket_url = required(offer, 'url', 'index.html congress offers')
    if not ticket_url.startswith('https://'):
        raise GenerationError('index.html: congress ticket URL must use HTTPS')
    organization = one_definition(home, 'index.html', ORGANIZATION_ID)
    return {'event': event, 'core': core, 'statistics': stats, 'ticket_url': ticket_url,
            'organization': core_organization(organization)}


def date_range(event):
    try:
        local_zone = ZoneInfo('Europe/Rome')
        start, end = (iso_datetime(event[field]).astimezone(local_zone)
                      for field in ('startDate', 'endDate'))
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise GenerationError(f'Cannot render congress dates in Europe/Rome: {error}') from error
    if start.year == end.year and start.month == end.month:
        return f'{start:%B} {start.day}-{end.day}, {start.year}'
    return f'{start:%B} {start.day}, {start.year} – {end:%B} {end.day}, {end.year}'


def location_label(event):
    place = event['location']
    address = place['address']
    country = {'IT': 'Italy'}.get(address['addressCountry'], address['addressCountry'])
    return f"{place['name']}, {address['addressLocality']} ({address['addressRegion']}), {country}"
