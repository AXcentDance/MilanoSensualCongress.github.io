"""Asset builders preserve complete outputs and track actual source changes."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import apply_responsive_images as apply_images
import build_fontawesome_subset as icons
import generate_responsive_images as images
import generation_support as support
import sync_social_meta as social


class AssetBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)
        return path

    def test_icon_discovery_includes_nested_public_and_utility_pages_and_shared_js(self):
        self.put('news/new/guide.html', "<i class='fa-regular fa-calendar'></i>")
        self.put('404.html', '<head><meta name="robots" content="noindex"></head><i class="fa-solid fa-house"></i>')
        self.put('js/new/dialog.js', 'element.innerHTML = `<i class="fa-brands fa-instagram"></i>`; icon.classList.add("fa-solid", "fa-bars");')
        self.put('output/draft.html', '<i class="fa-solid fa-draft"></i>')
        self.put('.quality/report.html', '<i class="fa-solid fa-report"></i>')
        found = icons.collect_icons(self.root)
        self.assertEqual(found, {'solid': {'house', 'bars'}, 'regular': {'calendar'}, 'brands': {'instagram'}})

    def font_fixture(self):
        self.put('index.html', '<i class="fa-solid fa-house"></i><i class="fa-brands fa-instagram"></i>')
        self.put('vendor/fontawesome/all.min.css', '.fa-house:before{content:"\\f015"}.fa-instagram:before{content:"\\f16d"}')
        self.put('vendor/fontawesome/fa-subset.min.css', 'old css')
        self.put('vendor/fontawesome/webfonts/fa-solid-900-subset.woff2', b'old solid')
        self.put('vendor/fontawesome/webfonts/fa-brands-400-subset.woff2', b'old brands')

    def test_unknown_required_icon_stops_without_changing_assets(self):
        self.font_fixture()
        self.put('new.html', '<i class="fa-solid fa-unknown"></i>')
        with patch.object(icons.importlib.util, 'find_spec', return_value=True), self.assertRaisesRegex(support.GenerationError, 'fa-|unknown'):
            icons.main(self.root)
        self.assertEqual((self.root / 'vendor/fontawesome/fa-subset.min.css').read_text(), 'old css')

    def test_missing_font_dependency_has_an_install_command(self):
        self.font_fixture()
        with patch.object(icons.importlib.util, 'find_spec', return_value=None), self.assertRaisesRegex(support.GenerationError, '-m pip install fonttools brotli'):
            icons.main(self.root)

    def test_later_font_conversion_failure_preserves_all_previous_outputs(self):
        self.font_fixture()
        def build(command, **kwargs):
            target = Path(next(arg.split('=', 1)[1] for arg in command if arg.startswith('--output-file=')))
            if 'brands' in target.name:
                return subprocess.CompletedProcess(command, 1, '', 'simulated bad font')
            target.write_bytes(b'new solid')
            return subprocess.CompletedProcess(command, 0, '', '')
        with patch.object(icons.importlib.util, 'find_spec', return_value=True), patch.object(icons, 'validate_glyphs'), patch.object(icons.subprocess, 'run', side_effect=build), self.assertRaisesRegex(support.GenerationError, 'simulated bad font'):
            icons.main(self.root)
        self.assertEqual((self.root / 'vendor/fontawesome/webfonts/fa-solid-900-subset.woff2').read_bytes(), b'old solid')
        self.assertEqual((self.root / 'vendor/fontawesome/fa-subset.min.css').read_text(), 'old css')

    def fake_tool(self, command):
        if command == ['cwebp', '-version']:
            return 'test encoder 1'
        if command[0] == 'ffprobe':
            return Path(command[-1]).read_text().split('|', 1)[0]
        if command[0] == 'cwebp':
            target = Path(command[-1])
            width = command[command.index('-resize') + 1]
            source = Path(command[command.index('-o') - 1])
            target.write_text(f'{width}|{source.read_text()}')
            return ''
        raise AssertionError(command)

    def build_images(self, tool=None):
        with patch.object(images.shutil, 'which', return_value='/tools/tool'), patch.object(images, 'run_tool', side_effect=tool or self.fake_tool), redirect_stdout(io.StringIO()):
            images.generate_variants(self.root)

    def test_same_filename_source_changes_and_corrupt_variants_are_rebuilt(self):
        self.put('images/artist.webp', '1600|first photograph')
        self.build_images()
        target = self.root / 'images/artist_480w.webp'
        first = target.read_bytes()
        stamp = target.stat().st_mtime_ns
        self.build_images()
        self.assertEqual(target.stat().st_mtime_ns, stamp)
        self.put('images/artist.webp', '1600|replacement photograph')
        self.build_images()
        replacement = target.read_bytes()
        self.assertNotEqual(first, replacement)
        target.write_bytes(b'corrupt derivative')
        self.build_images()
        self.assertEqual(target.read_bytes(), replacement)

    def test_cache_absence_and_recipe_changes_rebuild_safely(self):
        self.put('images/artist.webp', '1600|photo')
        self.build_images()
        cache = self.root / '.quality/responsive-images.json'
        cache.unlink()
        calls = []
        def record(command):
            calls.append(command)
            return self.fake_tool(command)
        self.build_images(record)
        self.assertEqual(sum(command[:2] == ['cwebp', '-q'] for command in calls), 3)
        calls.clear()
        with patch.object(images, 'QUALITY', 76):
            self.build_images(record)
        self.assertEqual(sum(command[:2] == ['cwebp', '-q'] for command in calls), 3)

    def test_no_upscaling_and_obsolete_larger_derivatives_removed(self):
        self.put('images/artist.webp', '1600|photo')
        self.build_images()
        self.put('images/artist.webp', '700|smaller replacement')
        self.build_images()
        self.assertTrue((self.root / 'images/artist_480w.webp').exists())
        self.assertFalse((self.root / 'images/artist_800w.webp').exists())
        self.assertFalse((self.root / 'images/artist_1200w.webp').exists())
        cache = json.loads((self.root / '.quality/responsive-images.json').read_text())
        self.assertEqual(set(cache['sources']['images/artist.webp']['variants']), {'480'})

    def test_conversion_failure_keeps_complete_previous_assets_and_cache(self):
        self.put('images/artist.webp', '1600|photo')
        self.build_images()
        previous = {file: file.read_bytes() for file in self.root.rglob('*') if file.is_file() and file.name != 'artist.webp'}
        self.put('images/artist.webp', '1600|new photo')
        def fail(command):
            if command[:2] == ['cwebp', '-q'] and command[command.index('-resize') + 1] == '1200':
                raise support.GenerationError('simulated conversion failure')
            return self.fake_tool(command)
        with self.assertRaisesRegex(support.GenerationError, 'simulated conversion failure'):
            self.build_images(fail)
        self.assertTrue(all(path.read_bytes() == data for path, data in previous.items()))

    def test_missing_tools_and_measurement_failures_are_actionable(self):
        self.put('images/artist.webp', '0|invalid width')
        with patch.object(images.shutil, 'which', return_value=None), self.assertRaisesRegex(support.GenerationError, 'brew install ffmpeg webp'):
            images.generate_variants(self.root)
        with self.assertRaisesRegex(support.GenerationError, 'Cannot measure.*width must be positive'):
            self.build_images()
        self.assertFalse((self.root / 'images/artist_480w.webp').exists())

    def test_application_refreshes_existing_generated_srcset_after_source_shrinks(self):
        self.put('images/artist.webp', '700|photo')
        self.put('images/artist_480w.webp', '480|photo')
        page = self.put('index.html', '<img src="images/artist.webp" srcset="images/artist_480w.webp 480w, images/artist_800w.webp 800w, images/artist.webp 1600w" sizes="220px" alt="Artist" loading="eager">')
        def dimensions(path):
            return (480 if '_480w' in str(path) else 700, 500)
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            with patch.object(apply_images, 'dims', side_effect=dimensions):
                apply_images.process_page('index.html')
        finally:
            os.chdir(previous)
        html = page.read_text()
        self.assertIn('images/artist.webp 700w', html)
        self.assertNotIn('800w', html)
        self.assertIn('sizes="220px"', html)
        self.assertIn('loading="eager"', html)

    def test_application_prepares_every_page_before_writing(self):
        first = self.put('index.html', 'previous homepage')
        second = self.put('it/index.html', 'previous Italian homepage')
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            with patch.object(apply_images, 'site_pages', return_value=['index.html', 'it/index.html']), patch.object(apply_images, 'process_page', side_effect=['changed homepage', support.GenerationError('cannot measure second page')]), self.assertRaises(support.GenerationError):
                apply_images.main()
        finally:
            os.chdir(previous)
        self.assertEqual(first.read_text(), 'previous homepage')
        self.assertEqual(second.read_text(), 'previous Italian homepage')

    def test_application_refreshes_versioned_srcset_and_preserves_query_and_fragment(self):
        self.put('images/artist.webp', '700|photo')
        self.put('images/artist_480w.webp', '480|photo')
        page = self.put('index.html', '<img src="images/artist.webp?v=2#preview" srcset="images/artist_480w.webp?v=1 480w, images/artist_800w.webp?v=1 800w, images/artist.webp?v=1 1600w" sizes="220px" alt="Artist" loading="eager">')
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            with patch.object(apply_images, 'dims', side_effect=lambda path: (480 if '_480w' in str(path) else 700, 500)):
                apply_images.process_page('index.html')
        finally:
            os.chdir(previous)
        html = page.read_text()
        self.assertIn('srcset="images/artist_480w.webp?v=2#preview 480w, images/artist.webp?v=2#preview 700w"', html)
        self.assertNotIn('_800w', html)
        self.assertNotIn('1600w', html)
        self.assertIn('sizes="220px"', html)

    def test_custom_srcset_query_or_image_remains_outside_generated_ownership(self):
        source = apply_images.urlsplit('/images/artist.webp?v=2')
        self.assertTrue(apply_images.generated_candidate('https://milanosensualcongress.com/images/artist_480w.webp?v=1 480w', source))
        self.assertFalse(apply_images.generated_candidate('/images/artist_480w.webp?crop=face 480w', source))
        self.assertFalse(apply_images.generated_candidate('/images/other_480w.webp?v=2 480w', source))
        self.assertFalse(apply_images.generated_candidate('https://example.com/images/artist_480w.webp?v=2 480w', source))

    def test_multidirectory_text_binary_outputs_support_same_basename(self):
        first = self.put('one/result', b'old binary')
        second = self.put('two/result', 'old text')
        support.write_outputs({first: b'new binary\x00', second: 'new text'})
        self.assertEqual(first.read_bytes(), b'new binary\x00')
        self.assertEqual(second.read_text(), 'new text')

    def test_multidirectory_replacement_failure_restores_text_binary_and_removals(self):
        first = self.put('one/result', b'old binary')
        second = self.put('two/result', 'old text')
        obsolete = self.put('three/obsolete', b'previous derivative')
        failed = self.put('three/z-failure', b'preserve me')
        original = Path.unlink
        def fail(path, *args, **kwargs):
            if path == failed:
                raise OSError('simulated removal failure')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail), self.assertRaisesRegex(support.GenerationError, 'Previous outputs are unchanged'):
            support.write_outputs({first: b'new binary', second: 'new text'}, remove=[obsolete, failed])
        self.assertEqual(first.read_bytes(), b'old binary')
        self.assertEqual(second.read_text(), 'old text')
        self.assertEqual(obsolete.read_bytes(), b'previous derivative')
        self.assertFalse(list(self.root.rglob('.generation-*')))

    def fake_dimensions(self, path):
        return tuple(map(int, Path(path).read_text().split('|', 1)[0].split(',')))

    def fake_social_conversion(self, command):
        source = Path(command[command.index('-i') + 1])
        width, height = self.fake_dimensions(source)
        height = min(round(height * 1200 / width), 630) if width >= 1200 else min(height, 630) if width >= 1000 else height
        Path(command[-1]).write_text(f'{min(width, 1200)},{height}|{source.read_text()}')
        return ''

    def test_generated_social_card_refreshes_from_provenance_after_clean_restart(self):
        source = self.put('images/source.webp', '1100,900|original')
        with patch.object(social, 'dims', side_effect=self.fake_dimensions), patch.object(social, 'run_tool', side_effect=self.fake_social_conversion) as convert:
            with social.CardBuild(self.root) as build:
                self.assertEqual(build.card('/images/source.webp'), ('/images/og/source.jpg', (1100, 630)))
                build.finish()
            self.assertNotIn('scale=', ' '.join(map(str, convert.call_args.args[0])))
            first = (self.root / 'images/og/source.jpg').read_bytes()
            source.write_text('1100,900|replacement')
            with social.CardBuild(self.root) as build:
                build.card('/images/og/source.jpg')
                build.finish()
        self.assertNotEqual(first, (self.root / 'images/og/source.jpg').read_bytes())

    def test_explicit_and_prebuilt_social_cards_are_not_inferred_from_webp_names(self):
        card = self.put('images/og/custom.jpg', '1200,630|authored card')
        self.put('images/custom.webp', '1600,900|different photo')
        self.put(social.BRAND_CARD.lstrip('/'), '1200,630|brand card')
        with patch.object(social, 'dims', side_effect=self.fake_dimensions), patch.object(social, 'run_tool', side_effect=AssertionError('must not regenerate authored card')):
            with social.CardBuild(self.root) as build:
                self.assertEqual(build.card('/images/og/custom.jpg')[0], '/images/og/custom.jpg')
                self.assertEqual(build.card('/images/logo.webp')[0], social.BRAND_CARD)
                build.finish()
        self.assertEqual(card.read_text(), '1200,630|authored card')
        self.assertFalse((self.root / 'images/og/generated-cards.json').exists())

    def test_social_generation_failure_keeps_existing_pages_cards_and_manifest(self):
        self.put('images/source.webp', '1600,900|photo')
        previous = self.put('index.html', 'previous page')
        with patch.object(social, 'dims', side_effect=self.fake_dimensions), patch.object(social, 'run_tool', side_effect=self.fake_social_conversion):
            with self.assertRaisesRegex(support.GenerationError, 'Required social source is missing'):
                with social.CardBuild(self.root) as build:
                    build.outputs[previous] = 'new page'
                    build.card('/images/source.webp')
                    build.card('/images/missing.webp')
                    build.finish()
        self.assertEqual(previous.read_text(), 'previous page')
        self.assertFalse((self.root / 'images/og/source.jpg').exists())
        self.assertFalse((self.root / 'images/og/generated-cards.json').exists())

    def test_social_required_metadata_is_structural_and_cannot_silently_skip(self):
        page = self.put('index.html', '<html><head><title>Artist &amp; Congress</title><meta content="A &amp; B" name="description"><link href="https://milanosensualcongress.com/" rel="canonical"><meta content="https://milanosensualcongress.com/images/og/card.jpg" property="og:image"></head><body></body></html>')
        self.put('images/og/card.jpg', '1200,630|card')
        with patch.object(social, 'dims', side_effect=self.fake_dimensions):
            with social.CardBuild(self.root) as build:
                output = social.process(str(page), build)
                self.assertEqual(output.count('property="og:image"'), 1)
                self.assertIn('content="A &amp; B"', output)
                self.assertIn('content="Artist &amp; Congress"', output)
                page.write_text('<head><title>Missing required metadata</title></head>')
                with self.assertRaisesRegex(support.GenerationError, 'expected one title, description, and canonical URL'):
                    social.process(str(page), build)


if __name__ == '__main__':
    unittest.main()
