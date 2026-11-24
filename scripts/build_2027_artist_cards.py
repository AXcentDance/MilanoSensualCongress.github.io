#!/usr/bin/env python3
"""Export the confirmed photographs for the existing website artist cards.

The original embedded photo layers are retained in a compact source bundle.
Website frames, headings and preview controls remain HTML/CSS. Older complete
flyer masters were removed at the owner's request; their photo pixels remain.
The two former placeholders use the approved official-photo cutouts below.
"""
from pathlib import Path
import base64
import hashlib
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from generation_support import run_generator, write_outputs

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'materials/2027/sources/website-artist-photo-sources-v31/website-artist-photo-sources-v31.zip'
CARDS = [
    ('Nacho y Silvia', 'nacho-silvia', 30, False),
    ('David y Ines', 'david-ines', 31, False),
    ('Gero y Migle', 'gero-migle', 32, False),
    ('Cristian y Gabriella', 'cristian-gabriella', 33, False),
    ('Agustin y Alba', 'agustin-alba', 34, False),
    ('Miguel y Sunsire', 'miguel-sunsire', 35, False),
    ('Klau y Ros', 'klau-ros', 36, False),
    ('Pablo y Raquel', 'pablo-raquel', 37, False),
    ('Luis y Andrea', 'luis-andrea', 38, False),
    ('Aitor', 'aitor', 39, False),
]
OFFICIAL_PHOTOS = {
    slug: ROOT / f'materials/2027/sources/rollup-canva-cutouts-v01/{slug}-canva-fitted.png'
    for slug in ('pablo-raquel', 'luis-andrea')
}


def main():
    outputs, records = {}, []
    with zipfile.ZipFile(SOURCE) as archive, tempfile.TemporaryDirectory(prefix='msc-2027-cards-') as temporary:
        for name, slug, layer, placeholder in CARDS:
            layer_path = f'EmeraldTenCouplesPromo/layers/layer{layer}.shapelayer/content.svg'
            official = OFFICIAL_PHOTOS.get(slug)
            if official:
                original_data = official.read_bytes()
            else:
                svg = ET.fromstring(archive.read(layer_path))
                photo = next(node for node in svg.iter() if node.tag == '{http://www.w3.org/2000/svg}image')
                encoded = photo.get('{http://www.w3.org/1999/xlink}href')
                assert encoded.startswith('data:image/png;base64,')
                original_data = base64.b64decode(encoded.split(',', 1)[1])
            original = Path(temporary) / f'{slug}.png'
            original.write_bytes(original_data)
            # The Aitor source is only 309 x 448. Retain its native detail;
            # the other nine confirmed photographs are larger.
            width, height, inset, top = (320, 384, 6, 16) if slug == 'aitor' else (800, 960, 16, 32)
            photo_width = width - 2 * inset
            filters = (f'scale={photo_width}:-1:flags=lanczos,format=rgba,'
                       f'crop={photo_width}:min(ih\\,{height - top}):0:0:exact=1,'
                       f'pad={width}:{height}:{inset}:{top}:color=0x00000000')
            suffix = 'official-home-portrait-v01' if official else 'portrait-v31'
            target = ROOT / f'images/artists/msc-2027-{slug}-{suffix}.webp'
            staged = Path(temporary) / target.name
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(original),
                            '-vf', filters, '-frames:v', '1',
                            '-c:v', 'libwebp', '-quality', '86', '-compression_level', '6', str(staged)], check=True)
            data = staged.read_bytes()
            outputs[target] = data
            records.append({'name': name, 'path': str(target.relative_to(ROOT)), 'width': width,
                            'height': height,
                            **({'sourcePhoto': str(official.relative_to(ROOT))} if official else {'sourceLayer': layer_path}),
                            'sourcePhotoSha256': hashlib.sha256(original_data).hexdigest(),
                            'filter': filters, 'nativeSourceWidth': int.from_bytes(original_data[16:20], 'big'),
                            'nativeSourceHeight': int.from_bytes(original_data[20:24], 'big'),
                            'photoPlaceholder': placeholder, 'bytes': len(data),
                            'sha256': hashlib.sha256(data).hexdigest()})
    qa = ROOT / '.quality/artist-cards-2027.json'
    qa.parent.mkdir(exist_ok=True)
    outputs[qa] = json.dumps({'source': str(SOURCE.relative_to(ROOT)),
                             'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                             'presentation': 'Previous website cards with flyer photographs; names and frames are HTML/CSS',
                             'cards': records}, indent=2) + '\n'
    write_outputs(outputs)
    print(f'Exported {len(records)} confirmed portraits for the existing website cards. No photo placeholders remain.')


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
