#!/usr/bin/env python3
"""Build size-appropriate copies of the owner's approved logo without redrawing it."""
from pathlib import Path
import subprocess
import tempfile

from generation_support import run_generator, write_outputs

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'images/brand/milano-sensual-congress-official-logo-source.png'
# Remove only empty black padding. The full supplied 4096px original is retained.
CROP = 'crop=3400:2040:200:800'
OUTPUTS = {
    'images/milano-sensual-congress-official-logo.webp': ('scale=1600:960:flags=lanczos', True),
    # Key the neutral black matte only for translucent navigation surfaces.
    # The supplied master, artwork colors and all other copies stay unchanged.
    'images/milano-sensual-congress-official-logo-nav.webp': ('scale=400:240:flags=lanczos,format=rgba,colorkey=0x000000:0.015:0.04', True),
    'images/milano-sensual-congress-official-logo-preview.webp': ('scale=950:570:flags=lanczos,pad=1200:630:(ow-iw)/2:(oh-ih)/2:black', True),
    'images/milano-sensual-congress-official-icon.webp': ('scale=180:108:flags=lanczos,pad=192:192:(ow-iw)/2:(oh-ih)/2:black', True),
    'images/og/milano-sensual-congress-official-social-card.jpg': ('scale=950:570:flags=lanczos,pad=1200:630:(ow-iw)/2:(oh-ih)/2:black', False),
}

def main():
    outputs = {}
    with tempfile.TemporaryDirectory(prefix='msc-logo-') as temporary:
        for name, (filters, webp) in OUTPUTS.items():
            staged = Path(temporary) / Path(name).name
            encoding = ['-c:v', 'libwebp', '-lossless', '1', '-compression_level', '6'] if webp else ['-q:v', '2']
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(SOURCE),
                            '-vf', CROP + ',' + filters, '-frames:v', '1', *encoding, str(staged)], check=True)
            outputs[ROOT / name] = staged.read_bytes()
    for destination in outputs:
        destination.parent.mkdir(parents=True, exist_ok=True)
    write_outputs(outputs)
    for destination, data in outputs.items():
        print(f'{destination.relative_to(ROOT)}: {len(data):,} bytes')


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
