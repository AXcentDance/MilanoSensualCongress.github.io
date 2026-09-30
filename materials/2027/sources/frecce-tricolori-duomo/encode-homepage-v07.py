"""Build the official-wordmark homepage derivatives without a baked-in year.

Older revisions and the reviewed v07 masters are preserved. Run the canonical
responsive-image generator afterwards to build the poster's bounded variants.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]
EXPORTS = ROOT / 'materials/2027/exports/video'
IMAGES = ROOT / 'images'
QA = ROOT / '.quality/frecce-tricolori-duomo/wordmark-v07'
SOURCES = {
    'msc-2027-duomo-wordmark-hero-intro-v07': EXPORTS / 'msc-2027-duomo-official-wordmark-intro-1920x1080-v07.mp4',
    'msc-2027-duomo-wordmark-ambient-loop-v07': EXPORTS / 'msc-2027-duomo-official-wordmark-loop-1920x1080-v07.mp4',
}
POSTER_SOURCE = EXPORTS / 'msc-2027-duomo-official-wordmark-intro-1920x1080-v07-poster.webp'
POSTER = IMAGES / 'msc-2027-duomo-wordmark-hero-poster-v07.webp'


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fast_start(path):
    data = path.read_bytes()
    positions = {}
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], 'big')
        atom = data[offset + 4:offset + 8].decode('ascii', errors='replace')
        if size == 1:
            size = int.from_bytes(data[offset + 8:offset + 16], 'big')
        if size == 0:
            size = len(data) - offset
        if size < 8:
            raise ValueError('Invalid MP4 atom')
        positions[atom] = offset
        offset += size
    return positions['moov'] < positions['mdat']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=int, choices=(480, 720, 1080), default=[1080, 720, 480])
    parser.add_argument('--skip-poster', action='store_true', help='Preserve the existing optimized poster and its variants')
    args = parser.parse_args()
    sizes = list(dict.fromkeys(args.sizes))
    # Even an economy-only build verifies the approved poster source and the
    # retained web poster before it writes any new MP4s.
    for source in [*SOURCES.values(), POSTER_SOURCE, *([POSTER] if args.skip_poster else [])]:
        if not source.exists():
            raise SystemExit(f'Finish and review the master first: {source}')
    targets = [IMAGES / f'{name}-{height}.mp4' for name in SOURCES for height in sizes]
    for target in [*targets, *([] if args.skip_poster else [POSTER])]:
        if target.exists():
            raise FileExistsError(f'Preserving existing derivative: {target}')
    QA.mkdir(parents=True, exist_ok=True)
    protected = [*SOURCES.values(), POSTER_SOURCE]
    protected += [path for path in IMAGES.glob('msc-2027-duomo-*') if path.is_file()]
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in protected}
    results = []
    for name, source in SOURCES.items():
        before = digest(source)
        recipes = {1080: ('2200k', '4400k', '25'), 720: ('1000k', '2000k', '25'), 480: ('400k', '800k', '28')}
        for height in sizes:
            bitrate, buffer, quality = recipes[height]
            target = IMAGES / f'{name}-{height}.mp4'
            print(f'Encoding {target.name}', flush=True)
            run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-i', str(source),
                 '-map', '0:v:0', '-an', '-vf', f'scale=-2:{height}:flags=lanczos',
                 '-c:v', 'libx264', '-preset', 'slow', '-crf', quality, '-maxrate', bitrate,
                 '-bufsize', buffer, '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                 '-level', '4.0' if height == 1080 else '3.1', '-g', '48',
                 '-movflags', '+faststart', str(target)])
            info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(target)]))
            video = info['streams'][0]
            expected_frames = 240 if 'intro' in name else 222
            assert video['codec_name'] == 'h264' and video['pix_fmt'] == 'yuv420p'
            assert video['height'] == height and video['avg_frame_rate'] == '24/1'
            assert int(video['nb_frames']) == expected_frames and len(info['streams']) == 1
            assert fast_start(target)
            run(['ffmpeg', '-v', 'error', '-i', str(target), '-f', 'null', '-'])
            results.append({'path': str(target.relative_to(ROOT)), 'bytes': target.stat().st_size,
                            'sha256': digest(target), 'sourceSha256': before,
                            'maxrate': bitrate, 'bufsize': buffer, 'faststart': True, 'probe': info})
    if not args.skip_poster:
        run(['cwebp', '-quiet', '-m', '6', '-q', '40', '-resize', '1440', '0', str(POSTER_SOURCE), '-o', str(POSTER)])
    poster_info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(POSTER)]))
    assert poster_info['streams'][0]['width'] == 1440 and poster_info['streams'][0]['height'] == 810
    for relative, fingerprint in hashes.items():
        assert digest(ROOT / relative) == fingerprint, f'Protected asset changed: {relative}'
    suffix = '-'.join(str(height) for height in sizes)
    (QA / f'web-verification-{suffix}.json').write_text(json.dumps({
        'videos': results, 'poster': str(POSTER.relative_to(ROOT)),
        'posterBytes': POSTER.stat().st_size, 'posterSha256': digest(POSTER),
        'posterProbe': poster_info, 'protectedSourceSha256': hashes,
        'protectedSourcesUnchanged': True, 'decodedWithoutErrors': True,
    }, indent=2) + '\n')
    print(f'{len(results)} web MP4s decoded successfully. Prior assets are unchanged.', flush=True)


if __name__ == '__main__':
    main()
