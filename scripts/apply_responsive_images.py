#!/usr/bin/env python3
"""Inject srcset/sizes into <img> tags for images that have responsive variants.

The `sizes` values below are NOT guesses: they were measured in a real browser
(offsetWidth at 375/768/1440px viewports) per page context, following the
"sizes truth rule". Re-measure before changing them.

Also fixes width/height to the intrinsic dimensions of the referenced file
(wrong ratios cause CLS) and applies the eager/lazy loading policy.

Run from the repo root: python3 scripts/apply_responsive_images.py
"""
import glob
import os
import re
import subprocess
from urllib.parse import urlsplit
from site_files import site_pages
from pathlib import Path

VARIANT_WIDTHS = [480, 800, 1200]

# (page glob, src substring, sizes) — first match wins.
# Measured: 375px / 768px / 1440px viewports, real rendered widths.
CONTEXT_RULES = [
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
        out = subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height',
             '-of', 'csv=p=0', path], stderr=subprocess.DEVNULL)
        w, h = out.decode().strip().splitlines()[0].split(',')
        _dims_cache[path] = (int(w), int(h))
    return _dims_cache[path]


def variants_for(fs_path):
    """Return [(width, variant_fs_path)] for existing ladder rungs of a file."""
    base, ext = os.path.splitext(fs_path)
    out = []
    for w in VARIANT_WIDTHS:
        v = f'{base}_{w}w{ext}'
        if os.path.exists(v):
            out.append((w, v))
    return out


def sizes_for(page, src, tag):
    is_hero = 'fetchpriority="high"' in tag or all(m in tag for m in EAGER_MARKERS) or (
        'w-full' in tag and 'h-full' in tag and 'absolute' in tag)
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


def process_page(page):
    html = orig = Path(page).read_text(encoding='utf-8')

    def rewrite(m):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]+)"', tag)
        if not src_m:
            return tag
        src = src_m.group(1)
        # Normalize absolute production URLs to local relative paths
        local_src = re.sub(r'https://milanosensualcongress\.com/', '/', src)
        parsed = urlsplit(local_src)
        if parsed.scheme or parsed.netloc:
            return tag
        fs_path = (parsed.path.lstrip('/') if parsed.path.startswith('/') else
                   os.path.normpath(os.path.join(os.path.dirname(page), parsed.path)))
        if not fs_path.endswith('.webp') or not os.path.exists(fs_path):
            return tag
        if src != local_src:
            tag = tag.replace(f'src="{src}"', f'src="{local_src}"')
            src = local_src

        w, h = dims(fs_path)
        # Fix intrinsic dimensions (wrong ratio = layout shift)
        tag = re.sub(r'\swidth="\d+"', '', tag)
        tag = re.sub(r'\sheight="\d+"', '', tag)
        tag = tag.replace('<img', f'<img width="{w}" height="{h}"', 1)

        rungs = variants_for(fs_path)
        sizes, is_hero = sizes_for(page, src, tag)
        if rungs and sizes and 'srcset=' not in tag:
            srcset = ', '.join(
                [f'{os.path.splitext(src)[0]}_{rw}w.webp {rw}w' for rw, _ in rungs]
                + [f'{src} {w}w'])
            tag = tag.replace(f'src="{src}"', f'src="{src}" srcset="{srcset}" sizes="{sizes}"', 1)

        # Loading policy: heroes eager+high priority, everything else lazy
        if is_hero:
            tag = re.sub(r'\sloading="\w+"', '', tag)
            tag = tag.replace('<img', '<img loading="eager"', 1)
            if 'fetchpriority=' not in tag:
                tag = tag.replace('<img', '<img fetchpriority="high"', 1)
        elif 'loading=' not in tag:
            tag = tag.replace('<img', '<img loading="lazy"', 1)
        if 'decoding=' not in tag:
            tag = tag.replace('<img', '<img decoding="async"', 1)
        return tag

    html = re.sub(r'<img[^>]*>', rewrite, html)
    if html != orig:
        Path(page).write_text(html, encoding='utf-8')
        return True
    return False


def main():
    pages = site_pages()
    changed = [p for p in pages if process_page(p)]
    print(f'{len(changed)} pages updated')


if __name__ == '__main__':
    main()
