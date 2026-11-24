#!/usr/bin/env python3
"""Build bounded, silent artist HLS previews from the retained source recordings."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import tempfile

from generation_support import run_generator, write_outputs

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / 'materials/2027/sources/website-artist-demos-20261023/preview-plan.json'
LEVELS = [(240, 180_000), (480, 600_000), (720, 1_000_000)]


def tracking_expression(points, axis, extent):
    """Interpolate the reviewed centres, using the existing smooth pan approach."""
    expression = f'{points[-1][axis] * extent:g}'
    for left, right in reversed(list(zip(points, points[1:]))):
        progress = f'((t-{left[0]:g})/{right[0] - left[0]:g})'
        eased = f'({progress}*{progress}*(3-2*{progress}))'
        centre = f'({left[axis] * extent:g}+{(right[axis] - left[axis]) * extent:g}*{eased})'
        expression = f'if(lt(t,{right[0]:g}),{centre},{expression})'
    return expression


def crop_filter(video, crop, duration):
    """Return an edge-to-edge 4:5 crop; never pad, stretch or upscale footage."""
    if not crop:
        return '', video['width'], video['height']
    width, height = crop['width'], crop['height']
    if not (isinstance(width, int) and isinstance(height, int) and
            0 < width <= video['width'] and 0 < height <= video['height'] and
            width % 2 == height % 2 == 0 and width * 5 == height * 4):
        raise ValueError('Crop must be an even, native-size 4:5 rectangle')
    points = crop['centres']
    if (len(points) < 2 or any(len(p) != 3 for p in points) or
            not all(math.isfinite(value) for point in points for value in point) or
            points[0][0] != 0 or points[-1][0] != duration or
            any(a[0] >= b[0] for a, b in zip(points, points[1:])) or
            any(not 0 <= value <= 1 for p in points for value in p[1:])):
        raise ValueError('Crop centres must cover the clip in time order, with normalized coordinates')
    x = tracking_expression(points, 1, video['width'])
    y = tracking_expression(points, 2, video['height'])
    return (f"crop={width}:{height}:x='clip({x}-{width / 2:g},0,iw-ow)':"
            f"y='clip({y}-{height / 2:g},0,ih-oh)',", width, height)


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def main():
    clips = json.loads(PLAN.read_text())['clips']
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artists', nargs='+', choices=[clip['slug'] for clip in clips])
    args = parser.parse_args()
    manifest = ROOT / '.quality/artist-previews-2027/manifest.json'
    selected = [clip for clip in clips if not args.artists or clip['slug'] in args.artists]
    retained = json.loads(manifest.read_text())['clips'] if args.artists and manifest.exists() else []
    rejected = json.loads((ROOT / '.agent/context/rejected-promo-sources.json').read_text())
    rejected_hashes = {item['sha256'] for item in rejected['rejectedSources']}
    outputs, records = {}, []
    with tempfile.TemporaryDirectory(prefix='msc-artist-hls-') as temporary:
        staging = Path(temporary)
        for clip in selected:
            name, slug = clip['artist'], clip['slug']
            source = ROOT / clip['source']
            start, duration, version = clip['startSeconds'], clip['durationSeconds'], clip['version']
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            assert source_hash not in rejected_hashes, 'Owner-rejected recording must never be reused'
            if clip.get('sourceSha256') and source_hash != clip['sourceSha256']:
                raise ValueError(f'{name}: source changed since the crop was reviewed')
            source_probe = probe(source)
            video = next(s for s in source_probe['streams'] if s['codec_type'] == 'video')
            assert 0 < duration <= 15 and start + duration <= float(source_probe['format']['duration'])
            fps = 25 if video['avg_frame_rate'] == '25/1' else 30
            crop, crop_width, crop_height = crop_filter(video, clip.get('crop'), duration)
            destination = ROOT / f'images/artists/msc-2027-{slug}-preview-{version}'
            master = ['#EXTM3U', '#EXT-X-VERSION:7', '#EXT-X-INDEPENDENT-SEGMENTS']
            levels = []
            for width, rate in LEVELS:
                assert width <= crop_width, 'Never upscale an artist recording or its crop'
                height = round(width * crop_height / crop_width / 2) * 2
                folder = staging / slug / str(width)
                folder.mkdir(parents=True)
                playlist = folder / 'index.m3u8'
                subprocess.run([
                    'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(start),
                    '-i', str(source), '-t', str(duration), '-map', '0:v:0', '-map_metadata', '-1', '-an',
                    '-vf', f'setpts=PTS-STARTPTS,{crop}scale={width}:{height}:flags=lanczos,setsar=1,fps={fps}',
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '24',
                    '-maxrate', str(rate), '-bufsize', str(rate * 2), '-pix_fmt', 'yuv420p',
                    '-profile:v', 'high', '-level:v', '4.0', '-bf', '0',
                    '-g', str(fps * 2), '-keyint_min', str(fps * 2), '-sc_threshold', '0',
                    '-hls_time', '2', '-hls_playlist_type', 'vod', '-hls_segment_type', 'fmp4',
                    '-hls_fmp4_init_filename', 'init.mp4',
                    '-hls_segment_filename', str(folder / 'segment-%03d.m4s'),
                    '-hls_flags', 'independent_segments', str(playlist)
                ], check=True)
                lines = playlist.read_text().splitlines()
                durations = [float(line.split(':', 1)[1].rstrip(',')) for line in lines if line.startswith('#EXTINF:')]
                fragments = sorted(folder.glob('segment-*.m4s'))
                assert len(fragments) == math.ceil(duration / 2)
                assert all(abs(value - 2) < .05 for value in durations[:-1])
                assert abs(sum(durations) - duration) < .05
                check = probe(playlist)
                stream = next(s for s in check['streams'] if s['codec_type'] == 'video')
                assert stream['width'] == width and stream['height'] == height
                assert all(s['codec_type'] != 'audio' for s in check['streams'])
                subprocess.run(['ffmpeg', '-v', 'error', '-i', str(playlist), '-f', 'null', '-'], check=True)
                # Keep a fast-start progressive fallback without a second encode.
                progressive = folder / 'preview.mp4'
                subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(playlist),
                                '-map', '0:v:0', '-map_metadata', '-1', '-c', 'copy', '-movflags', '+faststart', str(progressive)], check=True)
                total = sum(p.stat().st_size for p in fragments) + (folder / 'init.mp4').stat().st_size
                average = math.ceil(total * 8 / duration)
                bandwidth = math.ceil(max(p.stat().st_size * 8 / segment_duration
                                          for p, segment_duration in zip(fragments, durations)) * 1.05)
                master.extend([f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},AVERAGE-BANDWIDTH={average},'
                               f'RESOLUTION={width}x{height},FRAME-RATE={fps}.000,CODECS="avc1.640028"',
                               f'{width}/index.m3u8'])
                for path in folder.iterdir():
                    (destination / str(width)).mkdir(parents=True, exist_ok=True)
                    outputs[destination / str(width) / path.name] = path.read_bytes()
                levels.append({'width': width, 'height': height, 'fps': fps, 'rateCap': rate,
                               'bandwidth': bandwidth, 'averageBandwidth': average, 'streamBytes': total,
                               'segmentDurations': durations, 'maxSegmentBytes': max(p.stat().st_size for p in fragments),
                               'fallbackBytes': progressive.stat().st_size})
            outputs[destination / 'index.m3u8'] = '\n'.join(master) + '\n'
            records.append({'artist': name, 'slug': slug, 'source': str(source.relative_to(ROOT)),
                            'sourceSha256': source_hash,
                            'sourceWidth': video['width'], 'sourceHeight': video['height'],
                            'sourceFrameRate': video['avg_frame_rate'], 'sourceDuration': float(source_probe['format']['duration']),
                            'startSeconds': start, 'durationSeconds': duration,
                            'crop': clip.get('crop'), 'youtubeURL': clip.get('youtubeURL'),
                            'playlist': str((destination / 'index.m3u8').relative_to(ROOT)), 'levels': levels})
            print(f'{name}: verified {duration:g} seconds, three quality levels, independent segments.', flush=True)
    records = [record for record in retained if record['slug'] not in {clip['slug'] for clip in selected}] + records
    manifest.parent.mkdir(parents=True, exist_ok=True)
    outputs[manifest] = json.dumps({'clips': records, 'audio': False, 'upscaled': False}, indent=2) + '\n'
    write_outputs(outputs)


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
