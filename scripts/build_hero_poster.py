#!/usr/bin/env python3
"""Recompress the unchanged 2026 hero poster from its retained original."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from generate_responsive_images import run_tool
from generation_support import GenerationError, run_generator, write_outputs

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('images/sources/milano-sensual-congress-2026-hero-poster-source.webp')
OUTPUT = Path('images/poster.webp')
QUALITY = 40


def dimensions(path):
    result = json.loads(run_tool([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height', '-of', 'json', path,
    ]))
    stream = result['streams'][0]
    return stream['width'], stream['height']


def build(root=ROOT, *, check=False):
    source, destination = Path(root) / SOURCE, Path(root) / OUTPUT
    original = source.read_bytes()
    if dimensions(source) != (1280, 720):
        raise GenerationError('The approved 2026 poster source must remain 1280 x 720.')
    with tempfile.TemporaryDirectory(prefix='msc-hero-poster-') as temporary:
        staged = Path(temporary) / 'poster.webp'
        run_tool(['cwebp', '-quiet', '-q', str(QUALITY), '-m', '6', source, '-o', staged])
        if dimensions(staged) != (1280, 720):
            raise GenerationError('Poster conversion changed the approved dimensions.')
        encoded = staged.read_bytes()
        if not encoded or len(encoded) >= len(original):
            raise GenerationError('Poster conversion did not produce a smaller image.')
        if source.read_bytes() != original:
            raise GenerationError('Poster source changed during generation; previous output is unchanged.')
    if check:
        if not destination.exists() or destination.read_bytes() != encoded:
            raise GenerationError('Hero poster is stale; run python3 scripts/build_hero_poster.py.')
    else:
        write_outputs({destination: encoded})
    print(f'{OUTPUT}: {len(encoded):,} bytes, 1280 x 720, quality {QUALITY}, method 6; '
          f'sha256 {hashlib.sha256(encoded).hexdigest()}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify the output without replacing it')
    build(check=parser.parse_args().check)


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
