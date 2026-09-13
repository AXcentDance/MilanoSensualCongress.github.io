#!/usr/bin/env python3
"""Build bounded WebP derivatives; stage a complete build before replacing assets.

Requires ffprobe (FFmpeg) and cwebp (WebP tools). A content-hash cache in
.quality/responsive-images.json avoids rebuilding unchanged source/recipe/output
bytes. A missing or invalid cache safely rebuilds the variants on the next run.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from generation_support import GenerationError, run_generator, scan_error, write_outputs
from image_references import references_to
from site_files import ROOT

SEARCH_DIRS = ('images', 'spring/images')
VARIANTS = (480, 800, 1200)
QUALITY = 75
EXCLUDE_BASENAMES = {'poster', 'logo', 'qr-code', 'milano-sensual-congress-logo-preview'}


def run_tool(command):
    try:
        result = subprocess.run([str(value) for value in command], capture_output=True, text=True)
    except FileNotFoundError as error:
        raise GenerationError(f'{command[0]} is required. Install FFmpeg and WebP tools (macOS: brew install ffmpeg webp).') from error
    if result.returncode:
        raise GenerationError(f'{command[0]} failed for {command[-1]}: {result.stderr.strip()}')
    return result.stdout.strip()


def source_width(path):
    """A failed or nonpositive measurement must never disable no-upscaling."""
    try:
        output = run_tool(['ffprobe', '-v', 'error', '-show_entries', 'stream=width', '-of', 'csv=p=0', path])
        width = int(output.splitlines()[0])
        if width <= 0:
            raise ValueError('width must be positive')
        return width
    except Exception as error:
        raise GenerationError(f'Cannot measure {path}: {error}') from error


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources(root):
    for name in SEARCH_DIRS:
        folder = root / name
        if not folder.exists():
            continue
        for directory, dirs, files in os.walk(folder, onerror=scan_error):
            dirs[:] = sorted(name for name in dirs if not name.startswith('.'))
            for name in sorted(files):
                path = Path(directory, name)
                if (path.suffix.lower() == '.webp' and not name.startswith('.')
                        and not re.search(r'_\d+w$', path.stem)
                        and path.stem not in EXCLUDE_BASENAMES):
                    yield path


def generate_variants(root=ROOT):
    root = Path(root)
    for tool in ('ffprobe', 'cwebp'):
        if shutil.which(tool) is None:
            raise GenerationError(f'{tool} is required. Install FFmpeg and WebP tools (macOS: brew install ffmpeg webp).')
    recipe = {'widths': list(VARIANTS), 'quality': QUALITY, 'encoder': run_tool(['cwebp', '-version'])}
    cache_path = root / '.quality/responsive-images.json'
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
        if not isinstance(cache, dict) or not isinstance(cache.get('sources'), dict):
            cache = {}
    except (OSError, ValueError):
        cache = {}
    previous = cache.get('sources', {}) if cache.get('recipe') == recipe else {}
    records, outputs, removals = {}, {}, set()
    skipped = 0
    with tempfile.TemporaryDirectory(prefix='msc-images-') as temporary:
        for source in sources(root):
            relative = source.relative_to(root).as_posix()
            width = source_width(source)
            fingerprint = digest(source)
            before = previous.get(relative, {})
            if not isinstance(before, dict):
                before = {}
            old_variants = before.get('variants', {})
            if not isinstance(old_variants, dict):
                old_variants = {}
            record = {'sha256': fingerprint, 'variants': {}}
            for target_width in VARIANTS:
                target = source.with_name(f'{source.stem}_{target_width}w{source.suffix}')
                if target_width >= width:
                    if target.exists():
                        removals.add(target)
                    continue
                cached = old_variants.get(str(target_width))
                if before.get('sha256') == fingerprint and target.exists() and digest(target) == cached:
                    record['variants'][str(target_width)] = cached
                    skipped += 1
                    continue
                staged = Path(temporary) / f'{len(outputs)}.webp'
                run_tool(['cwebp', '-q', str(QUALITY), '-resize', str(target_width), '0', source, '-o', staged])
                if not staged.is_file() or staged.stat().st_size == 0:
                    raise GenerationError(f'Cannot generate {target}: cwebp produced no image')
                if source_width(staged) != target_width:
                    raise GenerationError(f'Cannot generate {target}: output width does not match {target_width}')
                outputs[target] = staged.read_bytes()
                record['variants'][str(target_width)] = digest(staged)
            # Refuse to publish derivatives if their input changed during generation.
            if digest(source) != fingerprint:
                raise GenerationError(f'{source} changed during generation; rerun after editing finishes')
            records[relative] = record
    if not records:
        raise GenerationError('No responsive-image sources found; check the images directories')
    if removals:
        references = references_to(removals, root)
        if references:
            raise GenerationError(
                'Cannot remove responsive derivatives that public HTML or CSS still references:\n'
                + '\n'.join(references)
                + '\nRun apply_responsive_images.py to prune generated srcsets after a source shrinks; '
                'review and update custom src/srcset/picture/CSS references explicitly, then rerun '
                'generate_responsive_images.py followed by apply_responsive_images.py. '
                'Existing generated assets and cache are unchanged.')
    cache_path.parent.mkdir(exist_ok=True)
    count = len(outputs)
    outputs[cache_path] = json.dumps({'recipe': recipe, 'sources': records}, indent=2, sort_keys=True) + '\n'
    write_outputs(outputs, remove=removals)
    print(f'Responsive images: {count} rebuilt, {skipped} unchanged, {len(removals)} obsolete oversized variants removed')


if __name__ == '__main__':
    raise SystemExit(run_generator(generate_variants))
