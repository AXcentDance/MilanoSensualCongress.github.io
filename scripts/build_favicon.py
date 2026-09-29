#!/usr/bin/env python3
"""Export the arrows-only favicon without changing the full official logo."""
from pathlib import Path
import struct
import subprocess
import tempfile

from generation_support import run_generator, write_outputs

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'images/brand/milano-sensual-congress-tricolor-spires-favicon-medium-source.png'
NAME = 'milano-sensual-congress-tricolor-spires-favicon-medium'


def main():
    images = {}
    with tempfile.TemporaryDirectory(prefix='msc-favicon-') as temporary:
        for size in (16, 32, 48, 192):
            staged = Path(temporary) / f'{size}.png'
            subprocess.run([
                'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(SOURCE), '-vf',
                # Resize premultiplied colour to avoid dark matte fringes.
                'format=gbrap,premultiply=inplace=1,'
                f'scale={size}:{size}:flags=lanczos,'
                'unpremultiply=inplace=1,format=rgba',
                '-frames:v', '1', '-compression_level', '9', str(staged),
            ], check=True)
            images[size] = staged.read_bytes()

    # ICO supports embedded PNG frames; keep native 16, 32 and 48 pixel sizes.
    sizes = (16, 32, 48)
    directory = bytearray(struct.pack('<HHH', 0, 1, len(sizes)))
    offset = 6 + 16 * len(sizes)
    for size in sizes:
        data = images[size]
        directory.extend(struct.pack('<BBBBHHII', size, size, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    outputs = {ROOT / 'favicon.ico': bytes(directory) + b''.join(images[size] for size in sizes)}
    for size in (32, 192):
        outputs[ROOT / f'images/{NAME}-{size}.png'] = images[size]
    write_outputs(outputs)
    for path, data in outputs.items():
        print(f'{path.relative_to(ROOT)}: {len(data):,} bytes')


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
