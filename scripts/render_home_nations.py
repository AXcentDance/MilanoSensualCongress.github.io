#!/usr/bin/env python3
"""Render the shared, progressively enhanced community section from its flag roster.

Run after changing data/community-2026.json, then run the normal critical-CSS
and sync:indexes workflows. --check verifies both language renderings read-only.
"""
import argparse
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- home-nations:start -->'
END = '<!-- home-nations:end -->'
FEATURED = ['IT', 'CH', 'DE', 'FR', 'ES', 'GB', 'NL', 'PL', 'RO', 'SE', 'PT', 'NO']
MILANO = (319.76, 362.42)
MAP_BOUNDS = (24, 24, 776, 596)
POCKET_CROP = (125, 165, 395, 365)
POCKET_LABELS = {'PT': (164, 361), 'ES': (212, 427), 'FR': (260, 326),
                 'GB': (250, 259), 'CH': (288, 388), 'DE': (378, 293),
                 'PL': (450, 297), 'RO': (473, 390), 'SE': (392, 210),
                 'IT': (374, 468)}
FLAG_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4 3'/%3E"
MAP_DIRECTIONS = {'N': (0, -1), 'NE': (1, -1), 'E': (1, 0), 'SE': (1, 1),
                  'S': (0, 1), 'SW': (-1, 1), 'W': (-1, 0), 'NW': (-1, -1)}

COPY = {
 'en': dict(title='Our Congress <em>in Numbers</em>',
  intro='Across Europe. Together in Milano. Celebrating the people who shared our dance floor in 2026.',
  chapter='Our community', destination='Our meeting point', passport='ONE COMMUNITY. MANY FLAGS.',
  selected='On the dance floor with', dancers='% of dancers', artists='Artists representing the country',
  pending='To be confirmed', statsHeading='2026 country statistics', country='Country',
  statsNote='Country statistics will be added as the figures are confirmed.',
  demoNote='Random demo figures for the layout preview.',
  facts=[('1,000+', 'dancers'), ('20+', 'nations'), ('20+', 'social hours')],
  directory='Find your flag.',
  search='Search for a country', clear='Clear',
  empty='No countries found. Try another name or country code.', results='{n} countries found', singular='1 country found',
  pocketTitle='The world dances <em>in Milano.</em>', pocketSelect='Choose a country', pocketExplore='Explore countries', pocketAll='All countries',
  pocketStatus='{country}: {percent} of dancers',
  pocketOutside='{country}: {percent} of dancers. Outside this map view.',
  pocketShare='Country share', pocketDemo='Preview figures',
  alt=''),
 'it': dict(title='Il nostro congresso <em>in numeri</em>',
  intro='Da tutta Europa. Insieme a Milano. Celebriamo chi ha condiviso la nostra pista nel 2026.',
  chapter='La community', destination='Il nostro punto d’incontro', passport='UNA COMMUNITY. TANTE BANDIERE.',
  selected='In pista insieme a', dancers='% dei ballerini', artists='Artisti che rappresentano il paese',
  pending='Da confermare', statsHeading='Statistiche per paese · 2026', country='Paese',
  statsNote='Le statistiche per paese saranno aggiunte quando i dati saranno confermati.',
  demoNote='Dati dimostrativi casuali per l’anteprima del layout.',
  facts=[('1.000+', 'ballerini'), ('20+', 'nazioni'), ('20+', 'ore di social')],
  directory='Trova la tua bandiera.',
  search='Cerca un paese', clear='Cancella',
  empty='Nessun paese trovato. Prova un altro nome o codice paese.', results='{n} paesi trovati', singular='1 paese trovato',
  pocketTitle='Il mondo balla <em>a Milano.</em>', pocketSelect='Scegli un paese', pocketExplore='Esplora i paesi', pocketAll='Tutti i paesi',
  pocketStatus='{country}: {percent} dei ballerini',
  pocketOutside='{country}: {percent} dei ballerini. Fuori da questa vista della mappa.',
  pocketShare='Quota per paese', pocketDemo='Dati dimostrativi',
  alt=''),
}

def esc(value):
 return html.escape(str(value), quote=True)

def statistics(country):
 """Unknown is null; a confirmed zero must remain a visible zero."""
 stats = country.get('statistics')
 if stats is None:
  stats = {}
 if not isinstance(stats, dict):
  raise ValueError('Country statistics must be an object')
 percent, artists = stats.get('dancerPercent'), stats.get('guestArtists')
 if percent is not None and (isinstance(percent, bool) or not isinstance(percent, (int, float))
     or not math.isfinite(percent) or not 0 <= percent <= 100):
  raise ValueError('dancerPercent must be a finite percentage from 0 to 100, or null')
 if artists is not None and (isinstance(artists, bool) or not isinstance(artists, int) or artists < 0):
  raise ValueError('guestArtists must be a nonnegative integer, or null')
 return percent, artists

def route_origin(country):
 """Keep the Europe view fixed, using its edge for approximate incoming routes."""
 mx, my = MILANO
 left, top, right, bottom = MAP_BOUNDS
 point = country.get('mapPoint')
 if point is not None:
  if (not isinstance(point, (list, tuple)) or len(point) != 2 or any(
      isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point)):
   raise ValueError('mapPoint must contain two finite coordinates')
  x, y = point
  if left <= x <= right and top <= y <= bottom and not country.get('offMap', False):
   return (x, y), False
  dx, dy = x - mx, y - my
 else:
  direction = country.get('mapDirection', '').upper()
  if direction not in MAP_DIRECTIONS:
   raise ValueError('A country outside the map needs a valid mapDirection')
  dx, dy = MAP_DIRECTIONS[direction]
 if dx == 0 and dy == 0:
  raise ValueError('An approximate route needs a direction away from Milano')
 # Scale the vector before intersection to avoid overflow for distant points.
 magnitude = max(abs(dx), abs(dy))
 dx, dy = dx / magnitude, dy / magnitude
 horizontal = (right - mx) / dx if dx > 0 else (left - mx) / dx if dx < 0 else math.inf
 vertical = (bottom - my) / dy if dy > 0 else (top - my) / dy if dy < 0 else math.inf
 distance = min(horizontal, vertical)
 return (round(mx + dx * distance, 2), round(my + dy * distance, 2)), True

def stat_text(value, lang, percent=False):
 if value is None:
  return COPY[lang]['pending']
 text = format(value, '.15g') if percent else str(value)
 if lang == 'it':
  text = text.replace('.', ',')
 return text + ('%' if percent else '')

def statistics_fallback(countries, lang, demo=False):
 c = COPY[lang]
 known = [r for r in countries if any(v is not None for v in statistics(r))]
 note = f'<p class="nations-statistics-note">{c["demoNote"] if demo else c["statsNote"]}</p>'
 if not known:
  return f'<noscript>{note}</noscript>'
 rows = ''.join(f'<tr><th scope="row">{esc(r["name"][lang])}</th><td>{stat_text(statistics(r)[0], lang, True)}</td><td>{stat_text(statistics(r)[1], lang)}</td></tr>' for r in known)
 return f'<noscript>{note}<table class="nations-statistics-table"><caption>{c["statsHeading"]}</caption><thead><tr><th scope="col">{c["country"]}</th><th scope="col">{c["dancers"]}</th><th scope="col">{c["artists"]}</th></tr></thead><tbody>{rows}</tbody></table></noscript>'

def curve(point, offset=(0, 0)):
 x,y=point;mx,my=MILANO
 bend=max(28, math.hypot(mx-x,my-y)*.32)
 left, top, right, bottom = MAP_BOUNDS
 control_x = min(right, max(left, (x + mx) / 2 - bend))
 control_y = min(bottom, max(top, min(y, my) - bend))
 ox, oy = offset
 return f'M{x-ox:g},{y-oy:g} Q{control_x-ox:g},{control_y-oy:g} {mx-ox:g},{my-oy:g}'

def mobile_community(countries, lang, demo=False):
 """A country-share map; all figures come from the same desktop roster."""
 c = COPY[lang]
 left, top, width, height = POCKET_CROP
 by_code = {r['code']: r for r in countries}
 selected = by_code['IT']
 selected_percent = stat_text(statistics(selected)[0], lang, True)
 status = c['pocketStatus'].format(country=selected['name'][lang], percent=selected_percent)
 note = c['pocketShare'] + (f' · {c["pocketDemo"]}' if demo else '')
 pins, leaders, options, rows = [], [], [], []
 for r in countries:
  code = r['code']
  (x, y), _ = route_origin(r)
  label_x, label_y = POCKET_LABELS.get(code, (x, y))
  value = statistics(r)[0]
  percentage = stat_text(value, lang, True)
  compact_percentage = '—' if value is None else percentage
  label = c['pocketStatus'].format(country=r['name'][lang], percent=percentage)
  hidden = '' if code in POCKET_LABELS else ' hidden'
  pins.append(f'<button class="nations-pocket-pin" type="button" data-mobile-country="{code}" aria-label="{esc(label)}" aria-pressed="{str(code == "IT").lower()}" style="left:{(label_x-left)/width*100:.6f}%;top:{(label_y-top)/height*100:.6f}%" disabled{hidden}><span>{code}</span><strong>{esc(compact_percentage)}</strong></button>')
  leaders.append(f'<g data-mobile-leader="{code}"{hidden}><line class="nations-pocket-leader" x1="{label_x-left:g}" y1="{label_y-top:g}" x2="{x-left:g}" y2="{y-top:g}"/><circle class="nations-pocket-dot" cx="{x-left:g}" cy="{y-top:g}" r="2"/></g>')
  options.append(f'<option value="{code}"{" selected" if code == "IT" else ""}>{esc(r["name"][lang])}</option>')
  rows.append(f'<tr><th scope="row">{esc(r["name"][lang])}</th><td>{esc(percentage)}</td></tr>')
 mx, my = MILANO[0]-left, MILANO[1]-top
 image = 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 800 620\'/%3E'
 image_style = f'left:{-left/width*100:.6f}%;top:{-top/height*100:.6f}%;width:{800/width*100:.6f}%;height:{620/height*100:.6f}%'
 return f'''<div class="nations-mobile" data-mobile-status-template="{esc(c['pocketStatus'])}" data-mobile-outside-template="{esc(c['pocketOutside'])}">
<header class="nations-pocket-heading"><p>{c['pocketTitle']}</p></header>
<div class="nations-pocket-view">
<img class="nations-pocket-base" data-nations-map-src="/images/europe-community-sculpted-emerald-country-borders.svg" src="{image}" style="{image_style}" alt="" width="800" height="620" decoding="async">
<noscript><img class="nations-pocket-base" src="/images/europe-community-sculpted-emerald-country-borders.svg" style="{image_style}" alt="" width="800" height="620" loading="lazy" decoding="async"></noscript>
<svg class="nations-pocket-lines" viewBox="0 0 395 365" width="395" height="365" fill="none" aria-hidden="true" focusable="false"><g class="nations-pocket-leaders">{''.join(leaders)}</g><path class="nations-pocket-route" d="{curve(route_origin(selected)[0], (left, top))}"/><g class="nations-pocket-destination" transform="translate({mx:g} {my:g})"><circle class="nations-pocket-milano-ring" cx="0" cy="0" r="10"/><circle class="nations-pocket-milano-dot" cx="0" cy="0" r="4"/><text class="nations-pocket-milano-label" x="0" y="-14" text-anchor="middle">MILANO</text></g></svg>
<div class="nations-pocket-pins">{''.join(pins)}</div>
</div>
<div class="nations-pocket-controls"><label for="nations-pocket-country">{c['pocketExplore']}</label><select class="nations-pocket-select" id="nations-pocket-country" aria-label="{c['pocketSelect']}" disabled>{''.join(options)}</select></div>
<p class="nations-pocket-status" aria-live="polite" aria-atomic="true">{esc(status)}</p>
<p class="nations-pocket-note">{note}</p>
<noscript><details class="nations-pocket-fallback"><summary>{c['pocketAll']}</summary><table class="nations-pocket-table"><caption>{c['statsHeading']}</caption><thead><tr><th scope="col">{c['country']}</th><th scope="col">{c['dancers']}</th></tr></thead><tbody>{''.join(rows)}</tbody></table></details></noscript>
</div>'''

def render(data,lang):
 c=COPY[lang]; countries=data['countries']; n=len(countries)
 demo=data.get('statisticsMode') == 'demo'
 facts=''.join(f'<span><strong>{value}</strong><small>{label}</small></span>' for value, label in c['facts'])
 by_code={r['code']:r for r in countries}
 ordered=[by_code[code] for code in FEATURED]+sorted([r for r in countries if r['code'] not in FEATURED],key=lambda r:r['name'][lang].casefold())
 selected=by_code['ES']; (x,y),selected_approximate=route_origin(selected); mx,my=MILANO
 selected_percent, selected_artists = statistics(selected)
 origins = {r['code']: route_origin(r) for r in countries}
 routes=''.join(f'<path d="{curve(origins[r["code"]][0])}"/>' for r in countries if not origins[r['code']][1])
 dots=''.join(f'<circle cx="{origins[r["code"]][0][0]}" cy="{origins[r["code"]][0][1]}" r="2.5"/>' for r in countries if not origins[r['code']][1])
 items=[]
 for r in ordered:
  code=r['code']; names=' '.join([*r['name'].values(),code])
  (route_x, route_y), approximate = origins[code]
  percent, artists = statistics(r)
  # Familiar alternatives remain searchable in both languages.
  aliases={'GB':'UK Britain Great Britain Gran Bretagna Inghilterra','CZ':'Czech Republic Repubblica Ceca','TR':'Turkey Turchia','VA':'Vatican Holy See Santa Sede Vaticano','MD':'Moldavia Moldova','NL':'Holland Olanda','BA':'Bosnia Herzegovina Erzegovina'}
  items.append(f'''<li><button class="nations-country" type="button" data-country="{code}" title="{esc(r['name'][lang])}" data-country-name="{esc(r['name'][lang])}" data-search="{esc(names+' '+aliases.get(code,''))}" data-map-x="{route_x}" data-map-y="{route_y}" data-map-approximate="{str(approximate).lower()}" data-dancer-percent="{'' if percent is None else percent}" data-guest-artists="{'' if artists is None else artists}" aria-pressed="false" disabled><picture><source media="(scripting: none)" srcset="/images/flags/{code.lower()}.webp"><img data-nations-flag-src="/images/flags/{code.lower()}.webp" src="{FLAG_PLACEHOLDER}" alt="" width="32" height="24" loading="lazy" decoding="async"></picture><span class="nations-country-name sr-only">{esc(r['name'][lang])}</span></button></li>''')
 return f'''{START}
<section class="home-nations" id="home-nations" aria-labelledby="nations-title" data-chapter="{esc(c['chapter'])}" data-result-template="{esc(c['results'])}" data-result-singular="{esc(c['singular'])}" data-stat-pending="{c['pending']}">
<div class="e27-wrap">
{mobile_community(ordered, lang, demo)}
<header class="nations-heading"><h2 id="nations-title">{c['title']}</h2><p class="nations-intro">{c['intro']}</p></header>
<p id="congress-facts">{facts}</p>
<div class="nations-stage">
<div class="nations-atlas" aria-hidden="true">
<img class="nations-map-base" data-nations-map-src="/images/europe-community-sculpted-emerald-coastlines.svg" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 620'/%3E" alt="" width="800" height="620" decoding="async">
<noscript><img class="nations-map-base" src="/images/europe-community-sculpted-emerald-coastlines.svg" alt="" width="800" height="620" loading="lazy" decoding="async"></noscript>
<svg class="nations-map" viewBox="0 0 800 620" width="800" height="620" fill="none" focusable="false"><g class="nations-route">{routes}</g><g class="nations-dots">{dots}</g><path class="nations-route-active" data-approximate="{str(selected_approximate).lower()}" d="{curve((x, y))}"/><circle class="nations-origin" cx="{x}" cy="{y}" r="3"{' hidden' if selected_approximate else ''}/><circle cx="{mx}" cy="{my}" r="16" fill="#bc3b28" opacity=".14"/><circle class="nations-milano-ring" cx="{mx}" cy="{my}" r="17"/><circle class="nations-milano" cx="{mx}" cy="{my}" r="4"/></svg>
<div class="nations-destination"><strong>MILANO</strong></div>
</div>
<aside class="nations-panel" aria-label="{esc(c['chapter'])}">
<div class="nations-passport" aria-label="{esc(c['selected'])}" hidden><p class="nations-passport-kicker">{c['passport']}</p><div class="nations-selected"><span class="nations-selected-flag"><img data-nations-flag-src="/images/flags/es.webp" src="{FLAG_PLACEHOLDER}" alt="" width="80" height="60" loading="lazy" decoding="async"></span><div><p class="nations-selected-label">{c['selected']}</p><h3 class="nations-selected-name" aria-live="polite" aria-atomic="true">{selected['name'][lang]}</h3></div></div><dl class="nations-stats" aria-live="polite" aria-atomic="true"><div><dt>{c['dancers']}</dt><dd class="nations-stat-value" data-nations-stat="dancers" data-pending="{str(selected_percent is None).lower()}">{stat_text(selected_percent, lang, True)}</dd></div><div><dt>{c['artists']}</dt><dd class="nations-stat-value" data-nations-stat="artists" data-pending="{str(selected_artists is None).lower()}">{stat_text(selected_artists, lang)}</dd></div></dl></div>
<div class="nations-directory">
<div class="nations-directory-head"><h3>{c['directory']}</h3></div>
<p class="nations-result sr-only" aria-live="polite" aria-atomic="true"></p>
<div class="nations-tools" hidden><label class="nations-search"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><span class="sr-only">{c['search']}</span><input type="search" placeholder="{c['search']}" autocomplete="off" aria-controls="nations-list"></label><button class="nations-clear" type="button">{c['clear']}</button></div>
<ul class="nations-list" id="nations-list">
{chr(10).join(items)}
</ul>
<p class="nations-empty" hidden>{c['empty']}</p>
</div>
</aside>
</div>
{statistics_fallback(ordered, lang, demo)}
</div>
</section>
{END}'''

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 data=json.loads((ROOT/'data/community-2026.json').read_text());failed=[]
 codes=[r['code'] for r in data['countries']]
 if len(codes)!=len(set(codes)):raise ValueError('Duplicate country code')
 if data['edition']!=2026:raise ValueError('Copy and roster must agree on the edition')
 for lang,file in [('en','index.html'),('it','it/index.html')]:
  path=ROOT/file;source=path.read_text();section=render(data,lang)
  pattern=re.compile(re.escape(START)+r'.*?'+re.escape(END),re.S)
  if START in source:new=pattern.sub(lambda _:section,source)
  else:
   anchor='<section aria-labelledby="artists-title"'
   if source.count(anchor)!=1:raise ValueError('Cannot locate homepage insertion point')
   new=source.replace(anchor,section+'\n'+anchor)
  if args.check:
   if new!=source:failed.append(file)
  elif new!=source:path.write_text(new)
 if failed:raise SystemExit('Stale community section: '+', '.join(failed))
 print('Homepage community section '+('fresh' if args.check else 'rendered')+' in English and Italian.')

if __name__=='__main__':main()
