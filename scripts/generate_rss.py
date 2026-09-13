#!/usr/bin/env python3
"""Generate RSS 2.0 feeds for the news sections (EN: /feed.xml, IT: /it/feed.xml).

Items come from news/*.html and it/news/*.html: title from <title>, description
from the meta description, link as the clean extensionless URL, pubDate from the
article's JSON-LD datePublished. Deterministic: lastBuildDate is the newest item
date, never "now", so regeneration without content changes is a no-op.
"""
import os
import html as html_mod
from email.utils import format_datetime
import xml.etree.ElementTree as ET
from article_metadata import article_entity, publication_datetime
from generation_support import GenerationError, read_page, run_generator, verify_outputs, write_outputs
from site_files import indexable_pages, page_url_path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = 'https://milanosensualcongress.com'

FEEDS = [
    {
        'src': 'news',
        'out': 'feed.xml',
        'title': 'Milano Sensual Congress — Bachata News & Guides',
        'link': f'{BASE_URL}/news',
        'self': f'{BASE_URL}/feed.xml',
        'description': 'Bachata congress news, artist spotlights, festival guides and dance insights from Milano Sensual Congress.',
        'language': 'en',
    },
    {
        'src': os.path.join('it', 'news'),
        'out': os.path.join('it', 'feed.xml'),
        'title': 'Milano Sensual Congress — News e Guide Bachata',
        'link': f'{BASE_URL}/it/news',
        'self': f'{BASE_URL}/it/feed.xml',
        'description': 'News sui congressi bachata, artisti, guide ai festival e consigli di ballo dal Milano Sensual Congress.',
        'language': 'it',
    },
]


def parse_article(path):
    soup = read_page(path)
    article = article_entity(soup, path)
    if article is None:
        return None
    title = soup.head.find('title') if soup.head else None
    title = title.get_text(' ', strip=True) if title else ''
    descriptions = [str(meta.get('content', '')).strip()
                    for meta in soup.head.find_all('meta')
                    if str(meta.get('name', '')).strip().lower() == 'description']
    if not title:
        raise GenerationError(f'{path}: article page title is missing or empty')
    if len(descriptions) != 1 or not descriptions[0]:
        raise GenerationError(f'{path}: article requires one nonempty meta description')
    dt = publication_datetime(article.get('datePublished'), path)
    rel = os.path.relpath(path, ROOT_DIR).replace(os.sep, '/')
    return {
        'title': title,
        'description': descriptions[0],
        'link': BASE_URL + page_url_path(rel),
        'dt': dt,
    }


def esc(s):
    return html_mod.escape(s, quote=False)


def build_feed(cfg, pages=None):
    if pages is None:
        pages = indexable_pages(ROOT_DIR)
    items = []
    for page in pages:
        if os.path.dirname(page) != cfg['src']:
            continue
        item = parse_article(os.path.join(ROOT_DIR, page))
        if item:
            items.append(item)
    items.sort(key=lambda i: (i['dt'], i['link']), reverse=True)
    if not items:
        return None
    last_build = format_datetime(items[0]['dt'])
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    out.append('  <channel>')
    out.append(f"    <title>{esc(cfg['title'])}</title>")
    out.append(f"    <link>{cfg['link']}</link>")
    out.append(f'    <atom:link href="{cfg["self"]}" rel="self" type="application/rss+xml"/>')
    out.append(f"    <description>{esc(cfg['description'])}</description>")
    out.append(f"    <language>{cfg['language']}</language>")
    out.append(f"    <lastBuildDate>{last_build}</lastBuildDate>")
    for item in items:
        out.append('    <item>')
        out.append(f"      <title>{esc(item['title'])}</title>")
        out.append(f"      <link>{item['link']}</link>")
        out.append(f"      <guid isPermaLink=\"true\">{item['link']}</guid>")
        out.append(f"      <description>{esc(item['description'])}</description>")
        out.append(f"      <pubDate>{format_datetime(item['dt'])}</pubDate>")
        out.append('    </item>')
    out.append('  </channel>')
    out.append('</rss>')
    xml = '\n'.join(out) + '\n'
    try:
        ET.fromstring(xml)
    except ET.ParseError as error:
        raise GenerationError(f"{cfg['out']}: generated RSS XML is invalid: {error}") from error
    return xml


def render_outputs():
    pages = indexable_pages(ROOT_DIR)
    outputs = {}
    for cfg in FEEDS:
        feed = build_feed(cfg, pages)
        if feed is None:
            raise GenerationError(f"No indexable dated articles for {cfg['out']}; refusing to leave a stale feed")
        outputs[os.path.join(ROOT_DIR, cfg['out'])] = feed
    return outputs


def main(check=False):
    outputs = render_outputs()
    (verify_outputs if check else write_outputs)(outputs)
    for name, feed in outputs.items():
        print(f"{'Verified' if check else 'Wrote'} {name} ({feed.count('<item>')} items)")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify freshness without writing')
    args = parser.parse_args()
    raise SystemExit(run_generator(lambda: main(check=args.check)))
