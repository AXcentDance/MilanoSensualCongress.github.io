#!/usr/bin/env python3
"""Encode a short live-site hero from the retained 2026 source.

Keep source seconds 2–14: the opening matches the existing poster, followed by
venue and dancing footage. No upscaling, audio or change to the original file.
All variants are staged and decoded before any production output is replaced.
"""
import json
from pathlib import Path
import subprocess
import tempfile

from generation_support import run_generator, write_outputs

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'images/hero-720.mp4'
VARIANTS = {360: (640, 29, '300k', '600k'),
            480: (854, 28, '500k', '1000k'),
            720: (1280, 27, '900k', '1800k')}


def main():
    outputs = {}
    with tempfile.TemporaryDirectory(prefix='msc-hero-') as temporary:
        for height, (width, crf, rate, buffer) in VARIANTS.items():
            name = f'milano-sensual-congress-2026-hero-loop-v1-{height}.mp4'
            staged = Path(temporary) / name
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                            '-ss', '2', '-i', str(SOURCE), '-t', '12', '-an',
                            '-vf', f'scale={width}:{height}:flags=lanczos,fps=24',
                            '-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf),
                            '-maxrate', rate, '-bufsize', buffer, '-pix_fmt', 'yuv420p',
                            '-profile:v', 'high', '-level:v', '3.1', '-movflags', '+faststart',
                            str(staged)], check=True)
            probe = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(staged)]))
            stream = probe['streams'][0]
            if (stream['codec_name'], stream['pix_fmt'], stream['width'], stream['height']) != ('h264', 'yuv420p', width, height):
                raise ValueError(f'Unexpected encoded format: {name}')
            if abs(float(probe['format']['duration']) - 12) > .1:
                raise ValueError(f'Unexpected clip duration: {name}')
            subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(staged), '-f', 'null', '-'], check=True)
            outputs[ROOT / 'images' / name] = staged.read_bytes()
    write_outputs(outputs)
    for destination, data in outputs.items():
        print(f'{destination.name}: {len(data):,} bytes')


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
