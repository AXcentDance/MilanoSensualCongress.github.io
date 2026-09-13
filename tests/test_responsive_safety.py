"""Image cleanup preserves authored choices and cannot delete public references."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import apply_responsive_images as apply_images
import generate_responsive_images as generate_images
from generation_support import GenerationError
from image_references import references_to


class ResponsiveSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def dimensions(self, path):
        return int(Path(path).read_text().split('|', 1)[0]), 500

    def apply(self, page='artists.html'):
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            with patch.object(apply_images, 'dims', side_effect=self.dimensions):
                return apply_images.process_page(page)
        finally:
            os.chdir(previous)

    def build(self):
        def run_tool(command):
            if command == ['cwebp', '-version']:
                return 'test encoder'
            if command[0] == 'ffprobe':
                return str(self.dimensions(command[-1])[0])
            if command[0] == 'cwebp':
                Path(command[-1]).write_text(command[command.index('-resize') + 1] + '|rebuilt')
                return ''
            raise AssertionError(command)
        with patch.object(generate_images.shutil, 'which', return_value='/fixture/tool'), \
             patch.object(generate_images, 'run_tool', side_effect=run_tool), \
             redirect_stdout(io.StringIO()):
            generate_images.generate_variants(self.root)

    def test_custom_single_quoted_srcset_and_sizes_are_preserved_without_duplicates(self):
        self.put('images/artists/artist.webp', '1600|photo')
        self.put('images/artists/artist_480w.webp', '480|variant')
        for quote in ["'", '"']:
            with self.subTest(quote=quote):
                path = self.put('artists.html', f'''<IMG SRC = 'images/artists/artist.webp'
                    SRCSET = {quote}images/artists/custom-crop.webp 480w{quote}
                    SIZES = {quote}50vw{quote} ALT='Artist > portrait' LOADING='eager'>''')
                self.apply()
                html = path.read_text()
                image = BeautifulSoup(html, 'html.parser').img
                self.assertEqual(image['srcset'], 'images/artists/custom-crop.webp 480w')
                self.assertEqual(image['sizes'], '50vw')
                self.assertEqual(image['loading'], 'eager')
                self.assertEqual(image['alt'], 'Artist > portrait')
                self.assertEqual(html.lower().count('srcset='), 1)
                self.assertEqual(html.lower().count('sizes='), 1)

    def test_generated_single_quoted_srcset_can_be_pruned_before_deletion(self):
        self.put('images/artists/artist.webp', '700|smaller replacement')
        self.put('images/artists/artist_480w.webp', '480|old variant')
        obsolete = self.put('images/artists/artist_800w.webp', '800|old variant')
        page = self.put('artists.html', '''<img src='images/artists/artist.webp'
            srcset='images/artists/artist_480w.webp 480w, images/artists/artist_800w.webp 800w, images/artists/artist.webp 1600w'
            sizes='220px' alt='Artist' loading='eager'>''')
        with self.assertRaisesRegex(GenerationError, 'artists.html.*artist_800w.webp'):
            self.build()
        self.assertTrue(obsolete.exists())
        self.apply()
        image = BeautifulSoup(page.read_text(), 'html.parser').img
        self.assertEqual(image['srcset'], 'images/artists/artist_480w.webp 480w, images/artists/artist.webp 700w')
        self.assertEqual(image['sizes'], '220px')
        self.build()
        self.assertFalse(obsolete.exists())

    def test_custom_source_references_block_removal_before_any_generated_output_changes(self):
        self.put('images/artists/artist.webp', '700|smaller replacement')
        old_small = self.put('images/artists/artist_480w.webp', '480|keep prior derivative')
        obsolete = self.put('images/artists/artist_800w.webp', '800|keep referenced derivative')
        cache = self.put('.quality/responsive-images.json', '{}')
        cases = {
            'img src': '<img src="images/artists/artist_800w.webp" alt="Artist">',
            'custom srcset': '<img src="images/artists/artist.webp" srcset="images/artists/artist_800w.webp?crop=face 800w" alt="Artist">',
            'picture source': '<picture><source srcset="/images/artists/artist_800w.webp 800w"><img src="images/artists/artist.webp" alt="Artist"></picture>',
            'preload': '<link rel="preload" as="image" imagesrcset="/images/artists/artist_800w.webp 800w">',
            'inline css': '<div style="background-image:url(images/artists/artist_800w.webp)"></div>',
            'style block': '<style>.hero{background:url("images/artists/artist_800w.webp")}</style>',
            'schema image': '<script type="application/ld+json">{"image":"https://milanosensualcongress.com/images/artists/artist_800w.webp"}</script>',
        }
        for kind, markup in cases.items():
            with self.subTest(kind=kind):
                page = self.put('artists.html', '<html><head></head><body>' + markup + '</body></html>')
                before = {path: path.read_bytes() for path in (old_small, obsolete, cache, page)}
                with self.assertRaisesRegex(GenerationError, 'Cannot remove responsive derivatives'):
                    self.build()
                self.assertTrue(all(path.read_bytes() == content for path, content in before.items()))

    def test_custom_srcset_is_not_rewritten_to_silence_a_deletion_conflict(self):
        self.put('images/artists/artist.webp', '700|smaller replacement')
        self.put('images/artists/artist_480w.webp', '480|variant')
        obsolete = self.put('images/artists/artist_800w.webp', '800|variant')
        page = self.put('artists.html', '''<img src='images/artists/artist.webp'
            srcset='images/artists/artist_800w.webp?crop=face 800w' sizes='50vw' alt='Artist'>''')
        self.apply()
        self.assertEqual(BeautifulSoup(page.read_text(), 'html.parser').img['srcset'],
                         'images/artists/artist_800w.webp?crop=face 800w')
        with self.assertRaisesRegex(GenerationError, 'review and update custom'):
            self.build()
        self.assertTrue(obsolete.exists())

    def test_css_files_imports_and_image_sets_protect_referenced_assets(self):
        target = self.put('images/artist_800w.webp', '800|variant')
        self.put('css/site.css', '@import "../styles/nested.css"; .hero{background:image-set("../images/artist_800w.webp" 1x)}')
        self.put('styles/nested.css', '.hero{background:url(../images/artist_800w.webp?v=2)}')
        self.assertEqual(references_to([target], self.root), [
            'css/site.css: ../images/artist_800w.webp',
            'styles/nested.css: ../images/artist_800w.webp?v=2'])

    def test_external_images_and_internal_reports_do_not_block_deletion(self):
        target = self.put('images/artist_800w.webp', '800|variant')
        self.put('index.html', '<img src="https://other.example/images/artist_800w.webp" alt="External">')
        self.put('output/draft.html', '<img src="/images/artist_800w.webp">')
        self.put('.quality/report.html', '<img src="/images/artist_800w.webp">')
        self.assertEqual(references_to([target], self.root), [])

    def test_unrelated_comments_and_script_templates_are_not_rewritten(self):
        self.put('images/artists/artist.webp', '700|photo')
        raw = "<img src='images/artists/artist.webp' alt='Example'>"
        page = self.put('artists.html', f'<!-- {raw} --><script>const template = "{raw}";</script>')
        self.assertFalse(self.apply())
        self.assertEqual(page.read_text(), f'<!-- {raw} --><script>const template = "{raw}";</script>')

    def test_navigation_logos_are_eager_without_hero_priority(self):
        cases = [
            ('images/brand.webp', '<nav><a class="brand" href="/">{image}<span>2026</span></a></nav>'),
            ('images/milano-sensual-congress-logo-nav.webp', '<nav><a class="flex items-center" href="/">{image}<span>2026</span></a></nav>'),
        ]
        for source, markup in cases:
            for attributes in ['', ' loading="lazy" fetchpriority="high"', ' loading="eager"']:
                with self.subTest(source=source, attributes=attributes):
                    self.put(source, '300|logo')
                    page = self.put('index.html', markup.format(image=f'<img src="{source}" alt="Congress logo"{attributes}>'))
                    self.apply('index.html')
                    soup = BeautifulSoup(page.read_text(), 'html.parser')
                    self.assertEqual(soup.img['loading'], 'eager')
                    self.assertNotEqual(soup.img.get('fetchpriority'), 'high')
                    self.assertEqual(soup.span.parent.name, 'a')
                    self.assertEqual(soup.span.get_text(), '2026')

    def test_unclassified_images_retain_loading_choices(self):
        self.put('images/small.webp', '100|small image')
        for loading in [None, 'lazy', 'eager']:
            with self.subTest(loading=loading):
                attribute = f' loading="{loading}"' if loading else ''
                page = self.put('index.html', '<a class="brand" href="/">Home</a>'
                                f'<img src="images/small.webp" alt="Small illustration"{attribute}>')
                self.apply('index.html')
                image = BeautifulSoup(page.read_text(), 'html.parser').img
                self.assertEqual(image.get('loading'), loading)
                self.assertNotIn('fetchpriority', image.attrs)

    def test_real_solo_guide_rewrite_keeps_following_year_outside_logo(self):
        # Keep the complete real document: the downstream parser's void-element
        # behavior depends on context that the isolated img fixture cannot model.
        relative = 'news/bachata-congress-alone-solo-dancer-guide.html'
        original = (Path(__file__).resolve().parents[1] / relative).read_text()
        baseline = re.sub(r'(<img\b[^>]*?)/\s*>', r'\1>', original)
        self.put('images/milano-sensual-congress-logo-nav.webp', '300|logo')
        page = self.put(relative, baseline)
        self.apply(relative)
        rewritten = page.read_text()
        soup = BeautifulSoup(rewritten, 'html.parser')
        brand = soup.select_one('nav a.brand')
        self.assertEqual(brand.img['loading'], 'eager')
        self.assertEqual(brand.span.parent, brand)
        self.assertEqual(brand.img.get_text(), '')
        self.assertEqual(brand.span.get_text(), '2026')
        self.assertEqual(soup.main.get_text(' ', strip=True),
                         BeautifulSoup(baseline, 'html.parser').main.get_text(' ', strip=True))
        self.assertNotRegex(rewritten, r'<img\b[^>]*logo-nav[^>]*?/\s*>')

    def test_existing_self_closed_logo_is_repaired_even_when_attributes_match(self):
        self.put('images/milano-sensual-congress-logo-nav.webp', '300|logo')
        page = self.put('index.html', '<a class="brand" href="/"><img src="images/milano-sensual-congress-logo-nav.webp" width="300" height="500" loading="eager" decoding="async" alt="Congress"/><span>2026</span></a>')
        self.assertTrue(self.apply('index.html'))
        self.assertNotIn('/><span>', page.read_text())
        self.assertFalse(self.apply('index.html'))


if __name__ == '__main__':
    unittest.main()
