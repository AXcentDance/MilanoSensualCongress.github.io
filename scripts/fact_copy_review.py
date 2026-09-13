"""Read-only candidate report for prose affected by changed congress facts.

This is a review aid, not an NLP correctness gate. Historical article prices,
third-party hotels/events and independent offers must be judged in context.
"""
import ast
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from event_facts import EVENT_ID, core_event, one_definition
from generation_support import GenerationError
from iso_dates import iso_datetime
from site_files import classified_pages


def price_constants(source):
    names = {'FULL_PASS_PRICE', 'FULL_PASS_VALID_THROUGH'}
    try:
        values = {}
        for node in ast.parse(source).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in names:
                        values[target.id] = ast.literal_eval(node.value)
        return {'Full Pass price': Decimal(values['FULL_PASS_PRICE']),
                'Full Pass deadline': iso_datetime(values['FULL_PASS_VALID_THROUGH'])}
    except (SyntaxError, ValueError, TypeError, KeyError, InvalidOperation) as error:
        raise GenerationError(f'Cannot read canonical price facts for copy review: {error}') from error


def snapshot(read, known_statistics=None):
    """Read facts without importing or executing historical Python source."""
    home = BeautifulSoup(read('index.html'), 'html.parser')
    event = one_definition(home, 'index.html', EVENT_ID)
    core = core_event(event, 'index.html')
    result = {field: value for field, value in core.items()
              if field in {'name', 'startDate', 'endDate'} or field.startswith('location.')}
    result['ticket destination'] = event.get('offers', {}).get('url')
    for language, soup in [('en', home), ('it', BeautifulSoup(read('it/index.html'), 'html.parser'))]:
        summary = soup.select_one('main #congress-facts')
        field = f'statistics ({language})'
        result[field] = summary.get_text(' ', strip=True) if summary else None
        # Adding the source id is not a statistics change when the exact same
        # paragraph was already visible before the annotation existed.
        if summary is None and known_statistics and soup.main:
            known = known_statistics.get(field)
            if known and any(p.get_text(' ', strip=True) == known for p in soup.main.find_all('p')):
                result[field] = known
    result.update(price_constants(read('scripts/update_price.py')))
    return result


def changed_categories(changes):
    categories = set()
    for field, (before, after) in changes.items():
        if field in {'startDate', 'endDate'}:
            categories.add('times')
            if before.astimezone(ZoneInfo('Europe/Rome')).date() != after.astimezone(ZoneInfo('Europe/Rome')).date():
                categories.add('dates')
        if field == 'name':
            categories.add('dates')
        if field.startswith('location.'):
            categories.add('venue')
        if field.startswith('Full Pass') or field == 'ticket destination':
            categories.add('offers')
        if field.startswith('statistics'):
            categories.add('statistics')
    return categories


PATTERNS = {
    'times': re.compile(r'\b(?:\d{1,2}[:.]\d{2}|\d{1,2}\s*(?:am|pm)|midnight|mezzanotte)\b', re.I),
    'dates': re.compile(r'\b(?:20\d\d|\d{1,2}[:.]\d{2}|january|february|march|april|may|june|july|august|september|october|november|december|gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\b', re.I),
    'venue': re.compile(r'\b(?:hotel|venue|location|sede|struttura|airport|aeroport\w*)\b', re.I),
    'offers': re.compile(r'€|\b(?:eur|full pass|masterclass|upgrade|ticket\w*|bigliett\w*|countdown|scadenza)\b', re.I),
    'statistics': re.compile(r'\d[\d.,]*\+|\b(?:dancers|ballerini|nations|nazioni|workshops?|social dancing)\b', re.I),
}


def candidate_snippets(soup, categories, values, previous_values=None):
    """Return readable source locations, never assert candidate text is wrong."""
    body = soup.body or soup.find('main')
    if body is None:
        return []
    sources = [values, previous_values or {}]
    venue_terms = [str(value).casefold() for source in sources for field, value in source.items()
                   if field in {'location.name', 'location.address.addressLocality'} and value]
    found = []
    seen = set()
    for node in body.find_all(['p', 'li', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                               'summary', 'label', 'button', 'a', 'time', 'div', 'span']):
        if node.find_parent(['script', 'style', 'nav', 'footer']) is not None:
            continue
        # Containers are useful for price badges, but their nested paragraphs
        # already provide better locations and must not be repeated wholesale.
        if node.name in {'div', 'span'} and node.find(['p', 'li', 'div', 'span', 'a', 'h1', 'h2', 'h3']):
            continue
        value = ' '.join(node.get_text(' ', strip=True).split())
        if not value or value in seen:
            continue
        matches = sorted(category for category in categories if PATTERNS[category].search(value)
                         or (category == 'venue' and any(term in value.casefold() for term in venue_terms))
                         or (category == 'offers' and node.name == 'a' and any(
                             node.get('href') == source.get('ticket destination') for source in sources
                             if source.get('ticket destination'))))
        if matches:
            seen.add(value)
            found.append((node.sourceline or '?', ', '.join(matches), value))
    return found


def review_copy(root, base='HEAD'):
    root = Path(root)
    try:
        revision = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', base + '^{commit}'],
                                  text=True, capture_output=True, check=True).stdout.strip()

        def previous(path):
            return subprocess.run(['git', '-C', str(root), 'show', revision + ':' + path],
                                  text=True, capture_output=True, check=True).stdout

        current = snapshot(lambda path: (root / path).read_text(encoding='utf-8'))
        old = snapshot(previous, known_statistics=current)
    except (OSError, subprocess.CalledProcessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        raise GenerationError(f'Cannot compare visible-copy facts against {base}: {detail}') from error
    changes = {field: (old[field], value) for field, value in current.items() if old[field] != value}
    if not changes:
        print(f'No shared source facts changed against {base}. This does not validate arbitrary prose.')
        return
    print(f'Visible-copy review against {base}:')
    for field, (before, after) in changes.items():
        print(f'- {field}: {before!s} -> {after!s}')
    print('Candidate passages below need contextual review; they are not automatically errors. '
          'Keep historical article facts and independent offers intact. Also inspect schedule images, '
          'countdowns and translated counterparts before release.')
    categories = changed_categories(changes)
    total = 0
    for page, soup, _indexable in classified_pages(root):
        snippets = candidate_snippets(soup, categories, current, old)
        for line, category, value in snippets:
            print(f'{page}:{line} [{category}] {value}')
        total += len(snippets)
    print(f'{total} candidate passages. Record reviewed pages and any intentional historical differences '
          'in the task result; this report does not certify all visible facts.')
