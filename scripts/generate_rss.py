#!/usr/bin/env python3
"""Generate RSS 2.0 feeds for the news sections (EN: /feed.xml, IT: /it/feed.xml).

Items come from news/*.html and it/news/*.html: title from <title>, description
from the meta description, link as the clean extensionless URL, pubDate from the
article's JSON-LD datePublished. Deterministic: lastBuildDate is the newest item
date, never "now", so regeneration without content changes is a no-op.
"""
import os
import re
import json
import html as html_mod
from datetime import datetime, timezone
from email.utils import format_datetime

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
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    title_m = re.search(r'<title>(.*?)</title>', content, re.S)
    desc_m = re.search(r'<meta name="description"\s+content=["\'](.*?)["\']', content, re.S)
    date = None
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', content, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for node in data.get('@graph', [data]):
            d = node.get('datePublished')
            if d:
                date = d
                break
        if date:
            break
    if not date:
        return None
    # Accept date-only or full ISO datetimes.
    try:
        if 'T' in date:
            dt = datetime.fromisoformat(date)
        else:
            dt = datetime.fromisoformat(date + 'T08:00:00+01:00')
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    rel = os.path.relpath(path, ROOT_DIR).replace(os.sep, '/')
    return {
        'title': html_mod.unescape(title_m.group(1).strip()) if title_m else os.path.basename(path),
        'description': html_mod.unescape(desc_m.group(1).strip()) if desc_m else '',
        'link': f"{BASE_URL}/{rel[:-len('.html')]}",
        'dt': dt,
    }


def esc(s):
    return html_mod.escape(s, quote=False)


def build_feed(cfg):
    src_dir = os.path.join(ROOT_DIR, cfg['src'])
    items = []
    for name in sorted(os.listdir(src_dir)):
        if not name.endswith('.html'):
            continue
        item = parse_article(os.path.join(src_dir, name))
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
    return '\n'.join(out) + '\n'


def main():
    for cfg in FEEDS:
        feed = build_feed(cfg)
        if feed is None:
            print(f"WARNING: no items for {cfg['out']}")
            continue
        out_path = os.path.join(ROOT_DIR, cfg['out'])
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(feed)
        print(f"Wrote {cfg['out']} ({feed.count('<item>')} items)")


if __name__ == '__main__':
    main()
