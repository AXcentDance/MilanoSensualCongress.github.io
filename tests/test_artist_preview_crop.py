"""Exercise the actual FFmpeg crop with a moving subject and boundary cases."""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_artist_hover_previews import crop_filter


class ArtistPreviewCropTests(unittest.TestCase):
    def test_invalid_crop_cannot_pad_or_stretch_the_source(self):
        video = {'width': 400, 'height': 200}
        points = [[0, .5, .5], [2, .5, .5]]
        for width, height in [(408, 510), (160, 202), (159, 200), (0, 0)]:
            with self.subTest(width=width, height=height), self.assertRaises(ValueError):
                crop_filter(video, {'width': width, 'height': height, 'centres': points}, 2)

    def test_tracking_must_cover_the_whole_clip_in_order(self):
        for points in ([[1, .5, .5], [2, .5, .5]],
                       [[0, .5, .5], [1, .5, .5]],
                       [[0, .5, .5], [0, .6, .5], [2, .5, .5]],
                       [[0, .5, .5], [2, 1.1, .5]]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                crop_filter({'width': 400, 'height': 200},
                            {'width': 160, 'height': 200, 'centres': points}, 2)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is needed to verify moving crops')
    def test_real_filter_follows_subject_instead_of_leaving_it_outside_frame(self):
        frames = bytearray()
        for frame in range(21):
            image = bytearray([20, 60, 40] * (400 * 200))
            centre = 100 + frame * 10
            for y in range(95, 105):
                for x in range(centre - 5, centre + 5):
                    offset = (y * 400 + x) * 3
                    image[offset:offset + 3] = bytes([240, 20, 20])
            frames.extend(image)
        crop, width, height = crop_filter({'width': 400, 'height': 200}, {
            'width': 160, 'height': 200,
            'centres': [[0, .25, .5], [1, .5, .5], [2, .75, .5], [2.1, .75, .5]],
        }, 2.1)
        result = subprocess.run([
            'ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '400x200', '-r', '10', '-i', '-', '-vf', crop.rstrip(','),
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-',
        ], input=frames, capture_output=True, check=True).stdout
        frame_bytes = width * height * 3
        self.assertEqual(len(result), 21 * frame_bytes)
        for frame in (0, 5, 10, 15, 20):
            offset = frame * frame_bytes + (100 * width + width // 2) * 3
            self.assertEqual(result[offset:offset + 3], bytes([240, 20, 20]))


if __name__ == '__main__':
    unittest.main()
