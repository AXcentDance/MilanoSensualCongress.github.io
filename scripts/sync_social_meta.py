#!/usr/bin/env python3
"""Synchronize social metadata and source-owned JPG cards as one complete build.

Existing explicit JPGs and PREBUILT cards are authoritative. Only cards recorded
in images/og/generated-cards.json are regenerated from a source image. This
provenance survives clean checkouts; it is not a public page or an LLM export.
"""
from pathlib import Path
from html import escape
import json
import re
import tempfile
from urllib.parse import unquote, urlsplit

from generation_support import BeautifulSoup, GenerationError, run_generator, write_outputs
from site_files import indexable_pages
from generate_responsive_images import digest, run_tool
from apply_responsive_images import dims, _dims_cache

SITE = 'https://milanosensualcongress.com'
BRAND_CARD = '/images/og/milano-sensual-congress-official-social-card.jpg'
THEME_COLOR = '#0f172a'
PREBUILT = {
    'logo.webp': BRAND_CARD,
    'milano-sensual-congress-logo-preview.webp': BRAND_CARD,
    'milano-sensual-congress-official-logo.webp': BRAND_CARD,
    'milano-sensual-congress-official-logo-nav.webp': BRAND_CARD,
    'milano-sensual-congress-official-logo-preview.webp': BRAND_CARD,
    'milano-sensual-congress-official-icon.webp': BRAND_CARD,
    'poster.webp': '/images/og/milano-sensual-congress-hero.jpg',
    'bachata-congress-2026-preview.webp': '/images/og/bachata-congress-2026-preview.jpg',
    'duomo-di-milano-bachata-italy-2026-dance-destination.webp': '/images/og/duomo-di-milano-bachata-2026.jpg',
}
RECIPE = {'max_width': 1200, 'max_height_for_wide_cards': 630, 'jpeg_quality': 4}


class CardBuild:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.manifest = self.root / 'images/og/generated-cards.json'
        self.outputs = {}
        self.cards = {}
        self.verified = set()
        self.original_manifest = self.manifest.read_text(encoding='utf-8') if self.manifest.exists() else ''
        try:
            self.records = json.loads(self.original_manifest) if self.original_manifest else {}
            if not isinstance(self.records, dict) or any(not isinstance(value, dict) for value in self.records.values()):
                raise ValueError('expected a mapping of generated cards to source records')
        except ValueError as error:
            raise GenerationError(f'{self.manifest}: invalid generation provenance: {error}') from error
        self.temporary = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.temporary is not None:
            self.temporary.cleanup()

    def local(self, url):
        parsed = urlsplit(url)
        if parsed.netloc and (parsed.scheme, parsed.netloc) != ('https', 'milanosensualcongress.com'):
            raise GenerationError(f'Unsupported external social image {url}; use an approved local card')
        if parsed.scheme and parsed.scheme != 'https':
            raise GenerationError(f'Unsupported social image URL: {url}')
        path = (self.root / unquote(parsed.path).lstrip('/')).resolve()
        if not path.is_relative_to(self.root):
            raise GenerationError(f'Social image escapes the website directory: {url}')
        return path

    def card(self, url):
        path = self.local(url or BRAND_CARD)
        relative = path.relative_to(self.root).as_posix()
        if path.name in PREBUILT:
            return self.card(PREBUILT[path.name])
        if relative in self.cards:
            return self.cards[relative]
        if path.suffix.lower() in {'.jpg', '.jpeg'}:
            if relative in self.records:
                source = self.records[relative].get('source')
                if not isinstance(source, str) or Path(source).suffix.lower() in {'.jpg', '.jpeg'}:
                    raise GenerationError(f'{self.manifest}: invalid source for {relative}')
                card = self.card(source)
                if card[0] != '/' + relative:
                    raise GenerationError(f'{self.manifest}: source does not generate {relative}')
                return card
            if not path.is_file():
                raise GenerationError(f'Required social card is missing: {path}')
            return '/' + relative, dims(str(path))
        if not path.is_file():
            raise GenerationError(f'Required social source is missing: {path}')
        output = 'images/og/' + path.stem + '.jpg'
        destination = self.root / output
        before = self.records.get(output, {})
        if before.get('source', relative) != relative:
            raise GenerationError(f'{destination}: another source owns this generated filename')
        if destination.exists() and not before:
            raise GenerationError(f'{destination}: existing card has no generation provenance. Reference this JPG directly to preserve it, or use a new source basename.')
        width, height = dims(str(path))
        source_hash = digest(path)
        current = (before.get('source_sha256') == source_hash and before.get('recipe') == RECIPE
                   and destination.exists() and digest(destination) == before.get('output_sha256'))
        if current:
            dimensions = dims(str(destination))
        else:
            if self.temporary is None:
                self.temporary = tempfile.TemporaryDirectory(prefix='msc-social-')
            staged = Path(self.temporary.name) / (str(len(self.outputs)) + '.jpg')
            command = ['ffmpeg', '-y', '-v', 'error', '-i', path]
            if width >= 1200:
                command += ['-vf', "scale=1200:-2,crop='min(1200,iw)':'min(630,ih)'"]
            elif width >= 1000:
                command += ['-vf', "crop=iw:'min(630,ih)'"]
            command += ['-q:v', str(RECIPE['jpeg_quality']), staged]
            run_tool(command)
            if not staged.is_file() or staged.stat().st_size == 0:
                raise GenerationError(f'{destination}: ffmpeg produced no image')
            dimensions = dims(str(staged))
            if dimensions[0] > width or dimensions[1] > height:
                raise GenerationError(f'{destination}: conversion enlarged the source image')
            if digest(path) != source_hash:
                raise GenerationError(f'{path} changed during generation; rerun after editing finishes')
            self.outputs[destination] = staged.read_bytes()
            self.records[output] = {'source': relative, 'source_sha256': source_hash,
                                    'output_sha256': digest(staged), 'recipe': RECIPE}
        result = ('/' + output, dimensions)
        self.cards[relative] = self.cards[output] = result
        return result

    def verify_card(self, url):
        """Check served JPG/provenance freshness without conversion or ffprobe."""
        if not url:
            raise GenerationError('Missing social image URL')
        path = self.local(url)
        relative = path.relative_to(self.root).as_posix()
        if relative in self.verified:
            return
        if path.suffix.lower() not in {'.jpg', '.jpeg'} or not path.is_file():
            raise GenerationError(f'{relative}: required social JPG is missing; run npm run sync:indexes')
        with path.open('rb') as image:
            if image.read(2) != b'\xff\xd8':
                raise GenerationError(f'{relative}: social card is not encoded as JPEG')
        if relative in self.records:
            record = self.records[relative]
            source_name = record.get('source')
            if not isinstance(source_name, str):
                raise GenerationError(f'{self.manifest}: invalid source for {relative}')
            source = self.local(source_name)
            if ('images/og/' + source.stem + '.jpg' != relative
                    or source.suffix.lower() in {'.jpg', '.jpeg'}):
                raise GenerationError(f'{self.manifest}: source does not generate {relative}')
            if (not source.is_file() or record.get('source_sha256') != digest(source)
                    or record.get('recipe') != RECIPE or record.get('output_sha256') != digest(path)):
                raise GenerationError(f'{relative}: generated social card is stale; run npm run sync:indexes')
        self.verified.add(relative)

    def finish(self):
        if self.records:
            self.manifest.parent.mkdir(parents=True, exist_ok=True)
            data = json.dumps(self.records, indent=2, sort_keys=True) + '\n'
            if data != self.original_manifest:
                self.outputs[self.manifest] = data
        write_outputs(self.outputs)


def process(path, build):
    html = orig = Path(path).read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    if soup.head is None:
        raise GenerationError(f'{path}: required head is missing')
    titles = soup.head.find_all('title')
    descriptions = soup.head.find_all('meta', attrs={'name': re.compile('^description$', re.I)})
    canonicals = soup.head.find_all('link', rel='canonical')
    if len(titles) != 1 or len(descriptions) != 1 or len(canonicals) != 1:
        raise GenerationError(f'{path}: expected one title, description, and canonical URL')
    title = titles[0].get_text().strip()
    desc = descriptions[0].get('content', '').strip()
    canonical = canonicals[0].get('href', '').strip()
    if not (title and desc and canonical):
        raise GenerationError(f'{path}: title, description, and canonical URL must not be empty')
    is_it = path.startswith('it/') or path.startswith('it\\')
    is_article = '/news/' in ('/' + path)
    locale, alt_locale = ('it_IT', 'en_US') if is_it else ('en_US', 'it_IT')
    old_image = soup.head.find('meta', attrs={'property': 'og:image'}) or soup.head.find('meta', attrs={'name': 'og:image'})
    card, (card_w, card_h) = build.card(old_image.get('content') if old_image else None)
    esc_title, desc, canonical = (escape(value, quote=False).replace('"', '&quot;') for value in (title, desc, canonical))

    def strip_social(match):
        tag = BeautifulSoup(match.group(), 'html.parser').find('meta')
        key = (tag.get('property') or tag.get('name') or '').lower()
        return '' if key.startswith(('og:', 'twitter:')) else match.group()
    html = re.sub(r'''[ \t]*<meta\b(?:[^>"']|"[^"]*"|'[^']*')*>\n?''', strip_social, html, flags=re.I)

    block = f'''  <meta property="og:type" content="{'article' if is_article else 'website'}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="{esc_title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{SITE}{card}">
  <meta property="og:image:width" content="{card_w}">
  <meta property="og:image:height" content="{card_h}">
  <meta property="og:image:alt" content="{esc_title}">
  <meta property="og:site_name" content="Milano Sensual Congress">
  <meta property="og:locale" content="{locale}">
  <meta property="og:locale:alternate" content="{alt_locale}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc_title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{SITE}{card}">
  <meta name="twitter:image:alt" content="{esc_title}">
'''
    anchor = '  <!-- Meta Pixel Code -->'
    if anchor in html:
        html = html.replace(anchor, block + anchor, 1)
    else:
        html = re.sub(r'([ \t]*)</head>', block + r'\1</head>', html, count=1, flags=re.I)

    # Add a missing theme color regardless of viewport attribute formatting.
    if soup.head.find('meta', attrs={'name': 'theme-color'}) is None:
        html = re.sub(r'</head>', '  <meta name="theme-color" content="' + THEME_COLOR + '">\n</head>', html, count=1, flags=re.I)

    return html if html != orig else None


def main():
    _dims_cache.clear()
    pages = indexable_pages()
    with CardBuild(Path.cwd()) as build:
        for path in pages:
            if (html := process(path, build)) is not None:
                build.outputs[Path(path).absolute()] = html
        build.finish()
    print(f'{len(pages)} pages normalized')


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
