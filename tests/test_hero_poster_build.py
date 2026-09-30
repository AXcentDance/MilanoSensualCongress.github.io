"""A failed poster build must not replace the published image."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_hero_poster as poster
from generation_support import GenerationError


class HeroPosterBuildTests(unittest.TestCase):
    def test_bad_converted_dimensions_preserve_existing_poster(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output = root / poster.SOURCE, root / poster.OUTPUT
            source.parent.mkdir(parents=True)
            source.write_bytes(b'original poster source')
            output.write_bytes(b'existing poster')

            def convert(command):
                Path(command[-1]).write_bytes(b'bad image')

            with patch.object(poster, 'run_tool', side_effect=convert), \
                    patch.object(poster, 'dimensions', side_effect=[(1280, 720), (1280, 719)]), \
                    self.assertRaisesRegex(GenerationError, 'dimensions'):
                poster.build(root)
            self.assertEqual(output.read_bytes(), b'existing poster')
            self.assertEqual(source.read_bytes(), b'original poster source')

    def test_check_mode_reports_staleness_without_replacing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output = root / poster.SOURCE, root / poster.OUTPUT
            source.parent.mkdir(parents=True)
            source.write_bytes(b'original poster source')
            output.write_bytes(b'existing poster')

            def convert(command):
                Path(command[-1]).write_bytes(b'new image')

            with patch.object(poster, 'run_tool', side_effect=convert), \
                    patch.object(poster, 'dimensions', return_value=(1280, 720)), \
                    self.assertRaisesRegex(GenerationError, 'stale'):
                poster.build(root, check=True)
            self.assertEqual(output.read_bytes(), b'existing poster')
