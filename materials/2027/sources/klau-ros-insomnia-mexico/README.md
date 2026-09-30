# Klau y Ros — Insomnia Mexico hover preview v01

The owner supplied `insomnia mexico.mp4` and requested its **01:08–01:28**
excerpt for the Klau y Ros picture on the 2027 homepage on 28 September 2026.
This is a local website edit, not a new confirmation of the 2027 lineup.

- Source: owner-supplied portrait recording, 1214 × 2160, approximately
  29.97 fps, 154.388 seconds. The full-length original stays outside Git.
- Source SHA-256: `8353b0c7cd395db4b6ab6f6d93f8e8b2932247f7e01bf68507fb44ab43631d7d`.
- Export: [HLS playlist](../../../../images/artists/klau-ros-insomnia-mexico-preview-v01/index.m3u8),
  `init.mp4` and `segment-000.m4s` through `segment-004.m4s` in the same folder.
- Format: 1080 × 1920 portrait, 30 fps, H.264 High level 4.0, 8-bit `yuv420p`,
  silent, 20 seconds in five independent 4-second fragments; 3 Mbit/s capped
  video bitrate with a 6 Mbit buffer. No audio is distributed in this preview.
- Presentation: same video on English and Italian homepages, zoomed to fill
  the portrait card with an upper-center crop and no side bars. The existing
  WebP artist picture stays visible until playback begins. All homepage artist
  demos are hover-only, as requested by the owner; clicking or tapping a card
  has no action.
- Loading: hover intent only; native HLS where supported, otherwise a small
  MediaSource reader. Leaving the card destroys the player and aborts pending
  application fetches. Reduced motion, data saving and touch retain the picture.
- Status: owner-requested local implementation, unpublished. The request
  authorizes this excerpt for the website; creator attribution and permissions
  for other channels are not documented here.

## Rebuild

Set `source_clip` to the original recording outside the repository. Run from
the repository root with FFmpeg and ffprobe installed. Preserve this revision
if creating an edit with different source content.

```sh
preview_dir=images/artists/klau-ros-insomnia-mexico-preview-v01
mkdir -p "$preview_dir"
ffmpeg -hide_banner -ss 68 -i "$source_clip" -t 20 -map 0:v:0 -an \
  -vf 'scale=1080:1920:flags=lanczos,setsar=1,fps=30' \
  -c:v libx264 -preset slow -crf 24 -maxrate 3M -bufsize 6M \
  -pix_fmt yuv420p -profile:v high -level:v 4.0 \
  -g 120 -keyint_min 120 -sc_threshold 0 \
  -hls_time 4 -hls_playlist_type vod -hls_segment_type fmp4 \
  -hls_fmp4_init_filename init.mp4 \
  -hls_segment_filename "$preview_dir/segment-%03d.m4s" \
  -hls_flags independent_segments "$preview_dir/index.m3u8"
ffprobe -v error -show_streams -show_format "$preview_dir/index.m3u8"
ffmpeg -v error -i "$preview_dir/index.m3u8" -f null -
```

The initialization segment and every media fragment must accompany the
playlist when the website changes are eventually published.
