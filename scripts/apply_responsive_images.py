#!/usr/bin/env python3
"""Inject srcset/sizes into <img> tags for images that have responsive variants.

The `sizes` values below are NOT guesses: they were measured in a real browser
(offsetWidth at 375/768/1440px viewports) per page context, following the
"sizes truth rule". Re-measure before changing them.

Also fixes width/height to the intrinsic dimensions of the referenced file
(wrong ratios cause CLS) and applies the eager/lazy loading policy.

Run from the repo root: python3 scripts/apply_responsive_images.py
"""
import os
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qsl, unquote, urlsplit
from site_files import site_pages
from pathlib import Path
from generation_support import BeautifulSoup, GenerationError, run_generator, write_outputs
from generate_responsive_images import VARIANTS, run_tool

VARIANT_WIDTHS = VARIANTS

# (page glob, src substring, sizes) — first match wins.
# Measured: 375px / 768px / 1440px viewports, real rendered widths.
CONTEXT_RULES = [
    # AS Cambiago card: measured 277 / 654 / 567px at 375 / 768 / 1440px.
    ('hotel.html', 'as-hotel-cambiago-entrance-fountain', '(max-width: 639px) calc(100vw - 98px), (max-width: 767px) 542px, (max-width: 1023px) 654px, (max-width: 1279px) 439px, (max-width: 1535px) 567px, 695px'),
    ('it/hotel.html', 'as-hotel-cambiago-entrance-fountain', '(max-width: 639px) calc(100vw - 98px), (max-width: 767px) 542px, (max-width: 1023px) 654px, (max-width: 1279px) 439px, (max-width: 1535px) 567px, 695px'),
    # Workshop feature poster: measured 333 / 335 / 488px at 375 / 768 / 1440px.
    ('news/bachata-workshop-levels-guide-congress.html', 'bachata-congress-milan-2026-workshop-levels', '(max-width: 640px) calc(100vw - 42px), (max-width: 900px) calc((100vw - 94px) / 2 - 2px), (max-width: 1050px) calc((100vw - 102px) / 2.15 - 2px), (max-width: 1181px) calc((100vw - 128px) / 2.15 - 2px), 488px'),
    ('it/news/livelli-workshop-bachata-congresso.html', 'bachata-congress-milan-2026-workshop-levels', '(max-width: 640px) calc(100vw - 42px), (max-width: 900px) calc((100vw - 94px) / 2 - 2px), (max-width: 1050px) calc((100vw - 102px) / 2.15 - 2px), (max-width: 1181px) calc((100vw - 128px) / 2.15 - 2px), 488px'),
    ('index.html', 'images/artists/', '(max-width: 640px) 50vw, 220px'),
    ('it/index.html', 'images/artists/', '(max-width: 640px) 50vw, 220px'),
    ('artists.html', 'images/artists/', '(max-width: 640px) 40vw, (max-width: 1024px) 29vw, 391px'),
    ('it/artists.html', 'images/artists/', '(max-width: 640px) 40vw, (max-width: 1024px) 29vw, 391px'),
    ('news.html', 'images/', '(max-width: 640px) 87vw, (max-width: 1024px) 41vw, 382px'),
    ('it/news.html', 'images/', '(max-width: 640px) 87vw, (max-width: 1024px) 41vw, 382px'),
    ('hotel.html', 'images/hotel/', '(max-width: 640px) 87vw, (max-width: 1024px) 93vw, 582px'),
    ('it/hotel.html', 'images/hotel/', '(max-width: 640px) 87vw, (max-width: 1024px) 93vw, 582px'),
    ('tickets.html', 'images/artists/', '184px'),
    ('it/tickets.html', 'images/artists/', '184px'),
    ('masterclass.html', 'HERO', '100vw'),
    ('it/masterclass.html', 'HERO', '100vw'),
    ('masterclass.html', 'images/artists/', '(max-width: 640px) 87vw, (max-width: 1024px) 29vw, 366px'),
    ('it/masterclass.html', 'images/artists/', '(max-width: 640px) 87vw, (max-width: 1024px) 29vw, 366px'),
    ('bachata-congress-2026.html', 'images/news/', '(max-width: 640px) 87vw, (max-width: 1024px) 93vw, 590px'),
    ('it/congresso-bachata-2026.html', 'images/news/', '(max-width: 640px) 87vw, (max-width: 1024px) 93vw, 590px'),
    ('transfer.html', 'transfer-car', '100vw'),
    ('it/transfer.html', 'transfer-car', '100vw'),
    ('contact.html', 'images/hotel/', '(max-width: 640px) 70vw, (max-width: 1024px) 85vw, 526px'),
    ('it/contact.html', 'images/hotel/', '(max-width: 640px) 70vw, (max-width: 1024px) 85vw, 526px'),
]

# Full-bleed background/hero <img>s that are the LCP of their page: load eager.
EAGER_MARKERS = ('object-cover', 'absolute')

_dims_cache = {}


def dims(path):
    if path not in _dims_cache:
        try:
            out = run_tool(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path])
            dimensions = tuple(map(int, out.splitlines()[0].split(',')))
            if len(dimensions) != 2 or min(dimensions) <= 0:
                raise ValueError('width and height must be positive')
            _dims_cache[path] = dimensions
        except Exception as error:
            raise GenerationError(f'Cannot measure {path}: {error}') from error
    return _dims_cache[path]


def variants_for(fs_path):
    """Return [(width, variant_fs_path)] for existing ladder rungs of a file."""
    base, ext = os.path.splitext(fs_path)
    out = []
    for w in VARIANT_WIDTHS:
        v = f'{base}_{w}w{ext}'
        if os.path.exists(v):
            # Old larger derivatives can remain on disk until references have
            # been safely pruned; they must not re-enter a smaller source's set.
            if w >= dims(fs_path)[0]:
                continue
            if dims(v)[0] != w:
                raise GenerationError(f'{v}: invalid responsive width; run generate_responsive_images.py before applying variants')
            out.append((w, v))
    return out


def sizes_for(page, src, tag):
    if isinstance(tag, str):
        tag = BeautifulSoup(tag, 'html.parser').find('img')
    classes = set(tag.get('class', []))
    is_hero = tag.get('fetchpriority') == 'high' or set(EAGER_MARKERS) <= classes or (
        {'w-full', 'h-full', 'absolute'} <= classes)
    for page_glob, needle, sizes in CONTEXT_RULES:
        if page != page_glob:
            continue
        if needle == 'HERO':
            if is_hero:
                return sizes, True
            continue
        if needle in src:
            return sizes, is_hero
    return None, is_hero


def generated_candidate(value, source):
    """Recognize this source's ladder without confusing URL queries with paths."""
    parts = value.strip().rsplit(None, 1)
    if len(parts) != 2 or not re.fullmatch(r'\d+w', parts[1]):
        return False
    candidate = urlsplit(re.sub(r'^https://milanosensualcongress\.com/', '/', parts[0]))
    if candidate.scheme or candidate.netloc:
        return False
    widths = '|'.join(map(str, VARIANT_WIDTHS))
    pattern = re.escape(os.path.splitext(source.path)[0]) + rf'(?:_(?:{widths})w)?\.webp'
    cache_only = lambda query: all(key == 'v' for key, _ in parse_qsl(unescape(query), keep_blank_values=True))
    same_query = candidate.query == source.query or (cache_only(candidate.query) and cache_only(source.query))
    return bool(re.fullmatch(pattern, candidate.path) and same_query
                and (not candidate.fragment or candidate.fragment == source.fragment))


def process_page(page, *, write=True):
    page = str(page)
    html = orig = Path(page).read_text(encoding='utf-8')

    def rewrite(raw, attributes, ancestors):
        if len({name for name, _ in attributes}) != len(attributes):
            raise GenerationError(f'{page}: duplicate image attributes must be resolved before rewriting')
        tag = BeautifulSoup(raw, 'html.parser').find('img')
        original_attributes = dict(tag.attrs)
        src = tag.get('src')
        if not src:
            return raw
        # Normalize absolute production URLs to local relative paths
        local_src = re.sub(r'https://milanosensualcongress\.com/', '/', src)
        parsed = urlsplit(local_src)
        if parsed.scheme or parsed.netloc:
            return raw
        path = unquote(parsed.path)
        fs_path = (path.lstrip('/') if path.startswith('/') else
                   os.path.normpath(os.path.join(os.path.dirname(page), path)))
        if not fs_path.endswith('.webp') or not os.path.exists(fs_path):
            return raw
        if src != local_src:
            tag['src'] = local_src
            src = local_src

        w, h = dims(fs_path)
        # Fix intrinsic dimensions (wrong ratio = layout shift)
        tag['width'], tag['height'] = str(w), str(h)

        rungs = variants_for(fs_path)
        sizes, is_hero = sizes_for(page, src, tag)
        is_brand_logo = 'logo-nav' in Path(path).name.lower() or any(
            name == 'a' and 'brand' in str(dict(attrs).get('class', '')).split()
            for name, attrs in ancestors)
        existing = tag.get('srcset')
        generated = existing is not None and all(
            generated_candidate(value, parsed)
            for value in existing.split(','))
        sizes = tag.get('sizes') or sizes
        if generated:
            del tag['srcset']
        if rungs and sizes and (existing is None or generated):
            srcset = ', '.join(
                [f'{parsed._replace(path=f"{os.path.splitext(parsed.path)[0]}_{rw}w.webp").geturl()} {rw}w' for rw, _ in rungs]
                + [f'{src} {w}w'])
            tag['srcset'], tag['sizes'] = srcset, sizes

        # A small brand logo is visible immediately but is not the LCP image.
        # Keep authored loading on other images: dimensions or a responsive
        # ladder do not tell us whether an unclassified image is below the fold.
        if is_brand_logo:
            tag['loading'] = 'eager'
            if tag.get('fetchpriority') == 'high':
                del tag['fetchpriority']
        elif is_hero:
            tag['loading'] = 'eager'
            if 'fetchpriority' not in tag.attrs:
                tag['fetchpriority'] = 'high'
        if 'decoding' not in tag.attrs:
            tag['decoding'] = 'async'
        rewritten = raw if tag.attrs == original_attributes else str(tag)
        # HTML img is void, not XML. A '/>' serialization can make the project's
        # downstream HTML parser attach following text to an img in real pages.
        return re.sub(r'/\s*>$', '>', rewritten)

    # HTMLParser finds actual image elements without interpreting examples in
    # comments or script strings as markup. Only changed image tags are serialized.
    offsets = [0]
    for line in html.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    replacements = []

    class ImageParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ancestors = []

        def handle_starttag(self, name, attributes):
            if name == 'img':
                line, column = self.getpos()
                start = offsets[line - 1] + column
                raw = self.get_starttag_text()
                replacement = rewrite(raw, attributes, self.ancestors)
                if replacement != raw:
                    replacements.append((start, start + len(raw), replacement))
            elif name not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'input',
                              'link', 'meta', 'param', 'source', 'track', 'wbr'}:
                self.ancestors.append((name, attributes))

        def handle_endtag(self, name):
            for index in range(len(self.ancestors) - 1, -1, -1):
                if self.ancestors[index][0] == name:
                    del self.ancestors[index:]
                    break

    parser = ImageParser()
    parser.feed(html)
    parser.close()
    for start, end, replacement in reversed(replacements):
        html = html[:start] + replacement + html[end:]
    if html != orig:
        if write:
            write_outputs({page: html})
            return True
        return html
    return False if write else None


def main():
    _dims_cache.clear()
    pages = site_pages()
    outputs = {page: html for page in pages if (html := process_page(page, write=False)) is not None}
    write_outputs(outputs)
    print(f'{len(outputs)} pages updated')


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
