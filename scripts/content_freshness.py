"""Record substantive page revisions independently of build and commit order.

Formatting, classes, inline/generated CSS, scripts, responsive delivery hints and
asset-only ?v= values are not editorial changes. Main content and media, body
navigation/form destinations, search/social metadata and structured facts are.
Existing verified revision dates were imported once from Git history. New
source changes are recorded once during synchronization; ordinary regeneration
and commits retain that recorded date.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from generation_support import BeautifulSoup, GenerationError
from iso_dates import iso_datetime


ASSET_SUFFIXES = {'.avif', '.webp', '.png', '.jpg', '.jpeg', '.gif', '.svg',
                  '.mp4', '.webm', '.mov', '.m3u8', '.woff', '.woff2', '.css', '.js', '.mjs'}
META_NAMES = {'description', 'robots', 'googlebot', 'author', 'keywords'}


def clean_text(value):
    return re.sub(r'\s+', ' ', str(value)).strip()


def stable_url(value):
    """Only known asset URLs use this repository's ?v= cache-version convention.

    Content-link query parameters remain significant, including a parameter named
    v. Other asset query parameters (crops, transformations, access tokens) remain.
    """
    value = clean_text(value)
    parts = urlsplit(value)
    if Path(parts.path).suffix.lower() not in ASSET_SUFFIXES:
        return value
    query = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True) if key != 'v']
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def image_identity(value):
    """Collapse the project's _NNNw derivative naming convention to its source.

    Keep distinct crops/basenames, extensions and non-version query parameters.
    Adding a same-image responsive rung does not change the page's subject.
    """
    parts = urlsplit(stable_url(value))
    path = re.sub(r'_\d+w(?=\.(?:avif|webp|png|jpe?g|gif)$)', '', parts.path, flags=re.I)
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def image_candidates(tag):
    candidates = {image_identity(tag[name]) for name in ('src', 'data-src') if tag.get(name)}
    for name in ('srcset', 'data-srcset'):
        for candidate in str(tag.get(name, '')).split(','):
            fields = candidate.strip().split()
            if fields:
                candidates.add(image_identity(fields[0]))
    return candidates


def main_media(main):
    """Track content identity across native/responsive/deferred media markup."""
    media = []
    for tag in main.find_all(['img', 'video', 'audio', 'iframe']):
        sources = set()
        if tag.name == 'img':
            sources.update(image_candidates(tag))
            picture = tag.find_parent('picture')
            if picture:
                for source in picture.find_all('source'):
                    sources.update(image_candidates(source))
        else:
            sources.update(stable_url(tag[name]) for name in ('src', 'data-src') if tag.get(name))
            for source in tag.find_all('source'):
                sources.update(stable_url(source[name]) for name in ('src', 'data-src') if source.get(name))
        media.append((tag.name, sorted(sources), image_identity(tag.get('poster', '')),
                      clean_text(tag.get('alt', '')), clean_text(tag.get('title', ''))))
    return media


def body_destinations(body):
    """Track labelled links/targets, deduplicating identical repeated menus."""
    destinations = set()
    if body:
        for tag in body.find_all(['a', 'area', 'form', 'input', 'button']):
            attribute = 'href' if tag.name in {'a', 'area'} else 'action' if tag.name == 'form' else 'formaction'
            if tag.has_attr(attribute):
                # Labels and their destinations belong together:
                # swapping Tickets/Hotel URLs must change the fingerprint.
                label = clean_text(tag.get('aria-label') or tag.get_text(' ', strip=True)
                                   or ' '.join(image.get('alt', '') for image in tag.find_all('img'))
                                   or tag.get('value', ''))
                destinations.add((attribute, stable_url(tag[attribute]), label))
    return sorted(destinations)


def css_images(css):
    """Retain image declarations and their selectors; ignore font URLs/colors."""
    result = []
    for selector, declarations in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        images = []
        for value in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)', declarations):
            if Path(urlsplit(value.strip()).path).suffix.lower() in {'.webp', '.avif', '.png', '.jpg', '.jpeg', '.svg', '.gif'}:
                images.append(image_identity(value.strip()))
        if images:
            # Minifiers remove spaces around selector punctuation without
            # changing which element owns the background image.
            selector = re.sub(r'\s*([,>+~])\s*', r'\1', clean_text(selector))
            result.append((selector, images))
    return result


def normalized_schema(value, key=None):
    if isinstance(value, dict):
        return {name: normalized_schema(item, name) for name, item in sorted(value.items())}
    if isinstance(value, list):
        result = [normalized_schema(item, key) for item in value]
        # Graph declaration order and a type-set's order do not change facts.
        if key in {'@graph', '@type'}:
            result.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
        return result
    if isinstance(value, str):
        return stable_url(value) if key in {'url', '@id', 'image', 'contentUrl', 'thumbnailUrl'} else clean_text(value)
    return value


def semantic_fingerprint(content, path='<page>'):
    try:
        soup = BeautifulSoup(content, 'html.parser')
        head = soup.head
        meta, links, schemas = [], [], []
        if head:
            for tag in head.find_all('meta'):
                name = str(tag.get('name', tag.get('property', ''))).strip().lower()
                if name in META_NAMES or name.startswith(('og:', 'twitter:', 'article:')):
                    value = clean_text(tag.get('content', ''))
                    if name in {'og:image', 'twitter:image', 'og:url'}:
                        value = stable_url(value)
                    meta.append((name, value))
            for tag in head.find_all('link', href=True):
                rel = {str(value).lower() for value in tag.get('rel', [])}
                if 'canonical' in rel or ('alternate' in rel and tag.get('hreflang')):
                    links.append((sorted(rel), tag.get('hreflang', ''), stable_url(tag['href'])))
            for tag in head.find_all('script'):
                if str(tag.get('type', '')).strip().lower() != 'application/ld+json':
                    continue
                schemas.append(normalized_schema(json.loads(tag.get_text())))
        destinations = body_destinations(soup.body)
        backgrounds = css_images('\n'.join(tag.get_text() for tag in soup.find_all('style')))
        for tag in soup.find_all(style=True):
            images = css_images('inline {' + tag['style'] + '}')
            if images:
                backgrounds.append((tag.name, clean_text(tag.get_text(' ', strip=True)), images))
        main = soup.find('main')
        if main is None and soup.body:
            main = soup.body
            for tag in main.find_all(['nav', 'footer']):
                tag.decompose()
        media, labels = [], []
        if main:
            for tag in main.find_all(['script', 'style', 'template', 'noscript']):
                tag.decompose()
            media = main_media(main)
            for tag in main.find_all(attrs={'aria-label': True}):
                labels.append(clean_text(tag['aria-label']))
        payload = {
            'language': soup.html.get('lang', '') if soup.html else '',
            'title': clean_text(head.title.get_text(' ', strip=True)) if head and head.title else '',
            'metadata': sorted(meta), 'headLinks': sorted(links),
            'schema': sorted(schemas, key=lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False)),
            'text': clean_text(main.get_text(' ', strip=True)) if main else '',
            'destinations': destinations, 'media': media, 'labels': labels,
            'headings': [(tag.name, clean_text(tag.get_text(' ', strip=True)))
                         for tag in main.find_all(re.compile(r'^h[1-6]$'))] if main else [],
            'backgrounds': backgrounds,
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    except Exception as error:
        raise GenerationError(f'{path}: cannot determine substantive content: {error}') from error


class PageRevisions:
    """The sitemap and this small revision record are written as one output set.

    A new content fingerprint is a new source revision, recorded at first sync.
    This is not an article publication date or a claim that it is already live.
    Read-only checks require the recorded fingerprint to match, and never advance
    a date. Once initialized, a checkout does not need historical Git objects.
    """
    def __init__(self, root, *, check=False):
        self.root = Path(root).resolve()
        self.path = self.root / 'scripts' / 'page_revisions.json'
        self.check = check
        self.now = datetime.now(timezone.utc)
        self.records = {}
        self.used = {}
        if not self.path.is_file():
            raise GenerationError(f'{self.path}: missing revision record; restore it from Git before generation')
        if self.path.is_file():
            try:
                payload = json.loads(self.path.read_text(encoding='utf-8'))
                if payload['version'] != 1 or not isinstance(payload['pages'], dict):
                    raise ValueError('unsupported revision record format')
                self.records = payload['pages']
            except (OSError, ValueError, KeyError, TypeError) as error:
                raise GenerationError(f'{self.path}: cannot load page revisions: {error}') from error

    def fingerprint(self, filepath):
        content = Path(filepath).read_text(encoding='utf-8')
        soup = BeautifulSoup(content, 'html.parser')
        # A content image changed in a linked stylesheet is significant too.
        # Read only image declarations, so generated CSS/font/color edits stay
        # technical changes and cannot refresh editorial dates.
        backgrounds = []
        for link in soup.find_all('link', href=True):
            if 'stylesheet' not in link.get('rel', []):
                continue
            url = urlsplit(link['href'])
            if url.scheme or url.netloc:
                continue
            css = ((self.root / url.path.lstrip('/')) if url.path.startswith('/')
                   else Path(filepath).parent / url.path).resolve()
            if self.root not in css.parents:
                raise GenerationError(f'{filepath}: stylesheet escapes the project: {link["href"]}')
            try:
                images = css_images(css.read_text(encoding='utf-8'))
            except OSError as error:
                raise GenerationError(f'{filepath}: cannot inspect stylesheet {css}: {error}') from error
            if images:
                backgrounds.append((css.relative_to(self.root).as_posix(), images))
        value = [semantic_fingerprint(content, filepath), backgrounds]
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    def lastmod(self, filepath):
        path = Path(filepath).resolve().relative_to(self.root).as_posix()
        fingerprint = self.fingerprint(filepath)
        record = self.records.get(path)
        if record is not None:
            try:
                stamp = iso_datetime(record['lastmod'])
                if stamp.tzinfo is None or stamp > self.now:
                    raise ValueError('date must have a timezone and cannot be in the future')
                if record['fingerprint'] == fingerprint:
                    self.used[path] = record
                    return record['lastmod']
            except (KeyError, TypeError, ValueError) as error:
                raise GenerationError(f'{self.path}: invalid revision for {path}: {error}') from error
        if self.check:
            raise GenerationError(f'{path}: substantive source revision is not synchronized; run npm run sync:indexes')
        lastmod = self.now.isoformat(timespec='seconds')
        self.used[path] = {'fingerprint': fingerprint, 'lastmod': lastmod}
        return lastmod

    def output(self):
        return {self.path: json.dumps({'version': 1, 'pages': self.used}, indent=2, sort_keys=True) + '\n'}
