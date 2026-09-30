# Frecce Tricolori above the Duomo — website source record

## Official wordmark v07 — without the year

Created on 28 September 2026 for the owner's homepage revision: retain the
approved official pink/purple and white wordmark over the Duomo and moving
tricolour footage, remove the separately composited gold year, and fill the
viewport horizontally at the natural 16:9 ratio. The surrounding date line
retains the confirmed 2027 edition. Both languages use the same film.

The film is an illustrative generated scene, not documentary footage. The
opening uses the selected v03 camera footage and the loop uses v05 ambient
footage, finished with the unchanged official logo crop. Wordmark proportions,
reveal timing (3.8–5.6 seconds), atmosphere and Duomo are preserved. Website
use follows the owner's requested implementation; wider campaign rights for
the initial reference are not recorded. Native generation takes, full source
history and unrelated review exports are preserved in the owner's workspace
and excluded from this release.

| Finished input | Specification |
| --- | --- |
| [Intro master](../../exports/video/msc-2027-duomo-official-wordmark-intro-1920x1080-v07.mp4) | 10 seconds, 240 frames |
| [Loop master](../../exports/video/msc-2027-duomo-official-wordmark-loop-1920x1080-v07.mp4) | 9.25 seconds, 222 frames |
| [Intro poster master](../../exports/video/msc-2027-duomo-official-wordmark-intro-1920x1080-v07-poster.webp) | Source for the bounded WebP poster |

The two short finished masters are silent 1920 × 1080, 24 fps H.264,
8-bit `yuv420p`, with fast-start metadata. Intro-to-loop handoff is at loop
time 1.25 seconds; the loop retains its 0.75-second background overlap.
They are finished encoder inputs, not the excluded native generation originals.

The [web encoder](encode-homepage-v07.py) produces capped 1080p, 720p and 480p
H.264 derivatives at 2200/1000/400 kbit/s, plus a 1440 × 810 WebP poster.
The [canonical image generator](../../../../scripts/generate_responsive_images.py)
produces 480/800/1200px responsive poster variants.

- Opening: [1080p](../../../../images/msc-2027-duomo-wordmark-hero-intro-v07-1080.mp4), [720p](../../../../images/msc-2027-duomo-wordmark-hero-intro-v07-720.mp4), [480p](../../../../images/msc-2027-duomo-wordmark-hero-intro-v07-480.mp4).
- Loop: [1080p](../../../../images/msc-2027-duomo-wordmark-ambient-loop-v07-1080.mp4), [720p](../../../../images/msc-2027-duomo-wordmark-ambient-loop-v07-720.mp4), [480p](../../../../images/msc-2027-duomo-wordmark-ambient-loop-v07-480.mp4).
- [Responsive poster source](../../../../images/msc-2027-duomo-wordmark-hero-poster-v07.webp).

## Encoding and delivery

The recipe requires FFmpeg, ffprobe and WebP tools. It checks all required
inputs before writing and refuses to overwrite retained v07 derivatives.
Use a new revision for a content change. To build missing economy variants
from the finished masters while retaining existing larger exports and poster:

```bash
python3 materials/2027/sources/frecce-tricolori-duomo/encode-homepage-v07.py --sizes 480 --skip-poster
```

For a fresh derivative build with none of its targets present, run the encoder
without those options, followed by `python3 scripts/generate_responsive_images.py`.
The existing checked-in exports do not need rebuilding to serve the website.

The 30 September economy variants preserve every frame and handoff: 461,868
bytes for the opening and 449,059 bytes for the loop (910,927 combined).
Both are 854 × 480, 24 fps, silent 8-bit H.264 with fast-start metadata.
The responsive poster uses quality 40, method 6: 9,524 / 17,364 / 27,268 bytes
at 480/800/1200px. Source-specific cache metadata prevents unrelated rebuilds.

The homepage shows the poster first, then attaches video after page load when
visible. It chooses 480p for reported 3G or downlink below 1.5 Mbit/s, 720p
up to a 1000px viewport or reported downlink below 4 Mbit/s, otherwise 1080p.
Save-Data, reduced motion, 2G and reported downlink below 0.4 Mbit/s retain
the poster. Without network hints it uses viewport fallback. Sources are
chosen once; playback pauses offscreen, when hidden, or when motion is disabled.

These are progressive MP4 clips with byte-range support, not adaptive HLS.
A browser may buffer the entire chosen clip. The separate artist HLS preview
and its hover/stop behavior are independent.

Prepared for the approved 2027 draft branch release. This does not publish
2027 content on the live 2026 site or approve unrelated promotional exports.
