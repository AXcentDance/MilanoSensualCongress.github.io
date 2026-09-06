#!/usr/bin/env python3
"""Normalize Open Graph / Twitter / theme-color metadata on every page.

- og:title mirrors <title>, og:description mirrors the meta description
- og:url mirrors the canonical URL; og:type is article for news pages
- og:image points at a dedicated JPG social card (scrapers still choke on WebP);
  JPG twins are generated on demand into images/og/ (1200x630 when the source
  is wide enough, native size otherwise, brand card as fallback)
- twitter:* mirrors og:*; og:locale/alternate set per language
- Adds <meta name="theme-color"> after the viewport meta

Run from the repo root: python3 scripts/sync_social_meta.py
"""
from site_files import site_pages
import os
import re
import subprocess

SITE = 'https://milanosensualcongress.com'
BRAND_CARD = '/images/og/milano-sensual-congress-social-card.jpg'
THEME_COLOR = '#0f172a'

# Pre-built cards for specific og:image sources (basename -> og path)
PREBUILT = {
    'logo.webp': BRAND_CARD,
    'milano-sensual-congress-logo-preview.webp': BRAND_CARD,
    'poster.webp': '/images/og/milano-sensual-congress-hero.jpg',
    'bachata-congress-2026-preview.webp': '/images/og/bachata-congress-2026-preview.jpg',
    'duomo-di-milano-bachata-italy-2026-dance-destination.webp': '/images/og/duomo-di-milano-bachata-2026.jpg',
}

_dims_cache = {}


def dims(path):
    if path not in _dims_cache:
        out = subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height',
             '-of', 'csv=p=0', path], stderr=subprocess.DEVNULL)
        w, h = out.decode().strip().splitlines()[0].split(',')
        _dims_cache[path] = (int(w), int(h))
    return _dims_cache[path]


def jpg_card_for(og_image_url):
    """Map an og:image URL to a local JPG card path, building it if needed."""
    if not og_image_url:
        return BRAND_CARD
    base = os.path.basename(og_image_url.split('?')[0])
    if base in PREBUILT:
        return PREBUILT[base]
    if base.endswith('.jpg') or base.endswith('.jpeg'):
        return og_image_url.replace(SITE, '')
    local = og_image_url.replace(SITE + '/', '')
    if not os.path.exists(local):
        return BRAND_CARD
    out = 'images/og/' + os.path.splitext(base)[0] + '.jpg'
    if not os.path.exists(out):
        w, _h = dims(local)
        if w >= 1000:
            vf = "scale=1200:-2,crop='min(1200,iw)':'min(630,ih)'"
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', local,
                            '-vf', vf, '-q:v', '4', out], check=True)
        else:
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', local,
                            '-q:v', '4', out], check=True)
    return '/' + out


def get_meta(html, pattern):
    m = re.search(pattern, html)
    return m.group(1).strip() if m else None


def process(path):
    html = orig = open(path).read()

    title = get_meta(html, r'<title>([^<]+)</title>')
    desc = get_meta(html, r'<meta\s+name="description"\s+content="([^"]*)"')
    canonical = get_meta(html, r'<link\s+rel="canonical"\s+href="([^"]*)"')
    if not (title and desc and canonical):
        return f'SKIP {path} (missing title/description/canonical)'

    is_it = path.startswith('it/') or path.startswith('it\\')
    is_article = '/news/' in ('/' + path)
    locale, alt_locale = ('it_IT', 'en_US') if is_it else ('en_US', 'it_IT')

    old_img = get_meta(html, r'<meta\s+(?:property|name)="og:image"\s*\n?\s*content="([^"]*)"')
    card = jpg_card_for(old_img)
    card_w, card_h = dims(card.lstrip('/'))

    esc_title = title.replace('&', '&amp;').replace('"', '&quot;') if '&amp;' not in title else title.replace('"', '&quot;')

    # Drop every existing og:/twitter: meta tag, then emit one canonical block
    html = re.sub(r'[ \t]*<meta[^>]*?(?:property|name)="(?:og:|twitter:)[^"]*"[^>]*?>\n?', '', html)

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
        html = re.sub(r'([ \t]*)</head>', block + r'\1</head>', html, count=1)

    # theme-color after the viewport meta
    if 'name="theme-color"' not in html:
        html = re.sub(
            r'(<meta name="viewport"[^>]*>)',
            r'\1\n  <meta name="theme-color" content="' + THEME_COLOR + '">',
            html, count=1)

    if html != orig:
        open(path, 'w').write(html)
        return None
    return None


def main():
    pages = site_pages()
    pages = [p for p in pages if os.path.basename(p) != '404.html']
    skipped = [r for p in pages if (r := process(p))]
    print(f'{len(pages) - len(skipped)} pages normalized')
    for s in skipped:
        print(s)


if __name__ == '__main__':
    main()
