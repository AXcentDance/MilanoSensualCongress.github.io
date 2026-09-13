"""Find public references before removing a responsive image derivative."""
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from generation_support import GenerationError, read_page, scan_error
from site_files import site_pages

CSS_URL = re.compile(r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^\s)]*))\s*\)''', re.I)
CSS_IMPORT = re.compile(r'''@import\s+["']([^"']+)["']''', re.I)


def local_reference(value, source, root):
    parsed = urlsplit(value.strip())
    if parsed.netloc and parsed.netloc.lower() not in {'milanosensualcongress.com', 'www.milanosensualcongress.com'}:
        return None
    if parsed.scheme and parsed.scheme.lower() not in {'http', 'https'}:
        return None
    if not parsed.path:
        return None
    path = unquote(parsed.path)
    target = (root / path.lstrip('/') if path.startswith('/') or parsed.netloc
              else source.parent / path).resolve()
    return target if target.is_relative_to(root) else None


def css_references(text):
    # Comments cannot request a resource. URL references include image-set(url()).
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    yield from (next(value for value in match if value) for match in CSS_URL.findall(text) if any(match))
    yield from CSS_IMPORT.findall(text)
    # CSS image-set also permits quoted URLs without url(...).
    for body in re.findall(r'(?:-webkit-)?image-set\(([^;}]*)', text, re.I):
        yield from re.findall(r'''["']([^"']+)["']''', body)


def json_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from json_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from json_strings(child)


def references_to(targets, root):
    """Return exact public HTML/CSS references to any proposed removal target."""
    root = Path(root).resolve()
    targets = {Path(target).resolve() for target in targets}
    references = set()
    pending_css = set()

    def inspect(value, source):
        target = local_reference(value, source, root)
        if target in targets:
            references.add(f'{source.relative_to(root).as_posix()}: {value}')
        if target is not None and target.suffix.lower() == '.css' and target.is_file():
            pending_css.add(target)

    for page in site_pages(root):
        source = root / page
        soup = read_page(source)
        for tag in soup.find_all(True):
            for attribute in ('src', 'href', 'poster', 'data-src'):
                if tag.get(attribute):
                    inspect(tag[attribute], source)
            for attribute in ('srcset', 'imagesrcset', 'data-srcset'):
                for candidate in tag.get(attribute, '').split(','):
                    if candidate.strip():
                        inspect(candidate.strip().split()[0], source)
            if tag.name == 'meta' and tag.get('content'):
                inspect(tag['content'], source)
            for value in css_references(tag.get('style', '')):
                inspect(value, source)
        for tag in soup.find_all('style'):
            for value in css_references(tag.get_text()):
                inspect(value, source)
        for tag in soup.find_all('script', attrs={'type': re.compile(r'^application/ld\+json$', re.I)}):
            try:
                data = json.loads(tag.string or tag.get_text())
            except ValueError as error:
                raise GenerationError(f'{page}: cannot verify image references in invalid JSON-LD: {error}') from error
            for value in json_strings(data):
                inspect(value, source)

    # Include published stylesheets even if a particular HTML page currently
    # does not link them. Imported and other linked local CSS is followed too.
    for name in ('css', 'vendor'):
        if not (root / name).is_dir():
            continue
        for directory, dirs, files in os.walk(root / name, onerror=scan_error):
            dirs[:] = [name for name in dirs if not name.startswith('.')]
            pending_css.update(Path(directory, name).resolve() for name in files
                               if name.lower().endswith('.css') and not name.startswith('.'))
    checked = set()
    while pending_css:
        source = pending_css.pop()
        if source in checked:
            continue
        checked.add(source)
        for value in css_references(source.read_text(encoding='utf-8')):
            inspect(value, source)
    return sorted(references)
