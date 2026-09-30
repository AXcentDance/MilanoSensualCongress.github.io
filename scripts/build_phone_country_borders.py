#!/usr/bin/env python3
"""Add projected Natural Earth country boundaries to the phone map variant.

Pass the pinned GeoJSON file via --source; this build never uses the network.
The source URL and checksum are recorded in images/europe-community-atlas-notes.md.
The coastlines asset used on desktop remains untouched.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = 'd42479fd79552cca4eec7f85fcdca717a790d29ff06be7676f1af0568c6d3f7c'
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)


def project(point):
    longitude, latitude = map(math.radians, point[:2])
    centre = math.radians(50)
    delta = longitude - math.radians(20)
    visible = math.sin(centre) * math.sin(latitude) + math.cos(centre) * math.cos(latitude) * math.cos(delta)
    if visible <= 0:
        return None
    return (400 + 610 * math.cos(latitude) * math.sin(delta),
            320 - 610 * (math.cos(centre) * math.sin(latitude) - math.sin(centre) * math.cos(latitude) * math.cos(delta)))


def projected_lines(geometry):
    lines = [geometry['coordinates']] if geometry['type'] == 'LineString' else geometry['coordinates']
    for line in lines:
        segment = []
        for point in line:
            projected = project(point)
            if projected is not None:
                segment.append(projected)
            else:
                if len(segment) > 1:
                    yield segment
                segment = []
        if len(segment) > 1:
            yield segment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise SystemExit('Unexpected boundary source. Use the pinned GeoJSON documented in the atlas notes.')
    data = json.loads(raw)
    tree = ET.parse(ROOT / 'images/europe-community-sculpted-emerald-coastlines.svg')
    surface = tree.find(f".//{{{SVG}}}g[@mask='url(#edge-vertical)']")
    borders = ET.SubElement(surface, f'{{{SVG}}}g', {
        'id': 'country-borders', 'fill': 'none', 'stroke': '#e0cf9b',
        'stroke-width': '.65', 'stroke-opacity': '.68',
        'stroke-linecap': 'round', 'stroke-linejoin': 'round',
    })
    for feature in data['features']:
        for points in projected_lines(feature['geometry']):
            xs, ys = zip(*points)
            if max(xs) < 0 or min(xs) > 800 or max(ys) < 0 or min(ys) > 620:
                continue
            path = 'M' + 'L'.join(f'{x:.2f},{y:.2f}' for x, y in points)
            ET.SubElement(borders, f'{{{SVG}}}path', {'d': path})
    output = ROOT / 'images/europe-community-sculpted-emerald-country-borders.svg'
    tree.write(output, encoding='unicode')
    print(f'{output.relative_to(ROOT)}: {len(borders)} boundary paths, {output.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
