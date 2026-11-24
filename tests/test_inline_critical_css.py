"""Critical CSS retains applicable logical selectors before async CSS loads."""
from pathlib import Path
from contextlib import redirect_stdout
import io
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import inline_critical_css as critical


class CriticalSelectorTests(unittest.TestCase):
    def test_scene_alternatives_keep_the_current_page_theme(self):
        selector = 'body.edition-2027:is(.scene-hotel,.scene-booking,.scene-contact)'
        for scene in ('scene-hotel', 'scene-booking', 'scene-contact'):
            with self.subTest(scene=scene):
                self.assertTrue(critical.keep_selector(selector, {'edition-2027', scene}))
        self.assertFalse(critical.keep_selector(selector, {'edition-2027', 'scene-artists'}))
        self.assertFalse(critical.keep_selector(selector, {'scene-hotel'}))

    def test_nested_alternatives_preserve_compound_and_outer_requirements(self):
        selector = '.edition-2027 :is(.hotel.ready, :where(.contact, .booking)) > .title'
        self.assertTrue(critical.keep_selector(selector, {'edition-2027', 'contact', 'title'}))
        self.assertTrue(critical.keep_selector(selector, {'edition-2027', 'hotel', 'ready', 'title'}))
        self.assertFalse(critical.keep_selector(selector, {'edition-2027', 'hotel', 'title'}))
        self.assertFalse(critical.keep_selector(selector, {'edition-2027', 'contact'}))

    def test_each_adjacent_pseudo_must_have_a_possible_branch(self):
        selector = '.card:is(.hotel,.contact):where(.ready,.loading)'
        self.assertTrue(critical.keep_selector(selector, {'card', 'contact', 'ready'}))
        self.assertFalse(critical.keep_selector(selector, {'card', 'contact'}))

    def test_element_and_state_alternatives_need_no_class(self):
        self.assertTrue(critical.keep_selector('.edition-2027 :is(h1,.headline)', {'edition-2027'}))
        self.assertTrue(critical.keep_selector('.button:IS(:hover,:focus-visible)', {'button'}))

    def test_not_does_not_require_excluded_or_nested_classes(self):
        selector = '.card:not(.hidden,:is(.disabled,.loading)) .title'
        self.assertTrue(critical.keep_selector(selector, {'card', 'title'}))
        # A page-level inventory cannot tell whether every card is hidden.
        self.assertTrue(critical.keep_selector(selector, {'card', 'title', 'hidden'}))
        self.assertFalse(critical.keep_selector(selector, {'card', 'hidden'}))
        self.assertTrue(critical.keep_selector('.card:is(:not(.hidden),.open)', {'card'}))

    def test_has_is_conservative_but_outer_requirements_stay_strict(self):
        selector = '.card:has(> .dynamic, :not(.hidden)) .title'
        self.assertTrue(critical.keep_selector(selector, {'card', 'title'}))
        self.assertFalse(critical.keep_selector(selector, {'card', 'dynamic'}))

    def test_escaped_classes_keep_their_exact_existing_meaning(self):
        cases = [
            (r'.md\:grid.grid', {'md:grid', 'grid'}),
            (r'.\32 xl\:grid', {'2xl:grid'}),
            (r'.w-\[50\%\]', {'w-[50%]'}),
            (r'.card\:is\(\.a\,\.b\)', {'card:is(.a,.b)'}),
            (r'.card:is(.md\:grid,.sm\:flex)', {'card', 'md:grid'}),
        ]
        for selector, classes in cases:
            with self.subTest(selector=selector):
                self.assertTrue(critical.keep_selector(selector, classes))
                for required in classes:
                    self.assertFalse(critical.keep_selector(selector, classes - {required}))

    def test_attribute_strings_do_not_become_class_or_pseudo_requirements(self):
        selector = '.card[data-label=".missing :is(.a,.b)"]:where([data-value="a,b)"],.other)'
        self.assertTrue(critical.keep_selector(selector, {'card'}))
        self.assertFalse(critical.keep_selector(selector, set()))

    def test_filtered_stylesheet_keeps_theme_type_and_motion_rules(self):
        css = '''
        body.edition-2027:is(.scene-hotel,.scene-booking,.scene-contact){background:#064c48}
        .edition-2027 :is(.stay-hotel-hero,.stay-contact-header) h1{font-family:Inter}
        .edition-2027 .unrelated{color:red}
        @media (prefers-reduced-motion:no-preference){
          .e27-motion-on:not(.e27-motion-paused) .stay-hotel-hero{animation:float 8s infinite}
          .missing,.stay-hotel-hero:where(:hover,:focus-visible){color:ivory}
        }
        '''
        classes = {'edition-2027', 'scene-hotel', 'stay-hotel-hero', 'e27-motion-on'}
        result = critical.filter_css(css, classes, {}, 'css')
        self.assertIn('background:#064c48', result)
        self.assertIn('font-family:Inter', result)
        self.assertIn('animation:float 8s infinite', result)
        self.assertIn('.stay-hotel-hero:where(:hover,:focus-visible)', result)
        self.assertNotIn('.unrelated', result)
        self.assertNotIn('.missing,', result)


class OptionalStylesheetTests(unittest.TestCase):
    def setUp(self):
        self.sources = {path: '' for path, _ in critical.CRITICAL_SOURCES}
        self.hrefs = ['/' + path + '?v=fixture' for path, _ in critical.CRITICAL_SOURCES]
        self.html = '<html><head></head><body class="edition-2027"></body></html>'

    def selected(self, html=None):
        html = self.html if html is None else html
        universe = critical.css_class_universe(self.sources)
        css = critical.build_critical_css(html, self.sources, universe)
        return critical.async_stylesheet_hrefs(html, css, self.sources, universe, self.hrefs)

    def test_zero_rule_optional_sheets_are_omitted_but_shared_sheets_stay(self):
        for path in critical.OPTIONAL_ASYNC_SOURCES:
            self.sources[path] = '.unrelated {color:red}@keyframes unused {to {opacity:1}}'
        expected = [href for href in self.hrefs
                    if href.split('?')[0].lstrip('/') not in critical.OPTIONAL_ASYNC_SOURCES]
        self.assertEqual(self.selected(), expected)
        self.assertEqual(len(expected), 7)

    def test_every_optional_sheet_is_retained_when_its_rules_apply(self):
        for path in critical.OPTIONAL_ASYNC_SOURCES:
            with self.subTest(path=path):
                self.sources[path] = '@media (max-width:700px){.edition-2027{color:ivory}}'
                self.assertIn('/' + path + '?v=fixture', self.selected())
                self.sources[path] = ''

    def test_runtime_safelist_keeps_rules_without_literal_markup_classes(self):
        self.sources['css/edition-stage.css'] = '.e27-motion-on .scene-progress{color:ivory}'
        self.assertIn('/css/edition-stage.css?v=fixture', self.selected())

    def test_needed_cross_sheet_keyframes_retain_their_owner(self):
        self.sources['css/edition-motion.css'] = '.e27-motion-on{animation:stage-orbit 2s infinite}'
        self.sources['css/edition-stage.css'] = (
            '@media (prefers-reduced-motion:no-preference){'
            '@keyframes stage-orbit{to{transform:rotate(1turn)}}}'
        )
        self.assertIn('/css/edition-stage.css?v=fixture', self.selected())

    def test_inline_animation_keeps_keyframe_only_sheet(self):
        self.sources['css/edition-stay.css'] = '@keyframes stay-glow{to{opacity:.5}}'
        html = self.html.replace('<body ', '<body style="animation:stay-glow 2s" ')
        self.assertIn('/css/edition-stay.css?v=fixture', self.selected(html))

    def test_fallback_retains_all_original_hrefs_and_order(self):
        css = 'body{color:ivory}'
        block = critical.build_block('', css, '0' * critical.HASH_LEN, self.hrefs,
                                     async_hrefs=self.selected())
        start, end, indent, recovered = critical.find_region(block, 'fixture.html')
        self.assertEqual((start, end, indent), (0, len(block), ''))
        self.assertEqual(recovered, self.hrefs)
        self.assertEqual(block.count('media="print"'), 7)
        fallback = block.split('<noscript data-critical-fallback>', 1)[1]
        self.assertEqual(critical.HREF_RE.findall(fallback), self.hrefs)
        self.assertIn('>' + css + '</style>', block)

    def test_critical_rules_follow_every_async_link_and_precede_the_fallback(self):
        css = '.headline{font:900 80px Inter}'
        block = critical.build_block('  ', css, '0' * critical.HASH_LEN, self.hrefs,
                                     async_hrefs=self.selected())
        before, after = block.split('<style data-critical=', 1)
        self.assertEqual(critical.HREF_RE.findall(before), self.selected())
        self.assertNotIn('<link', after.split('<noscript', 1)[0])
        self.assertIn('>' + css + '</style>\n  <noscript', block)
        self.assertTrue(all(line.startswith('  ') for line in block.splitlines()))

    def test_region_recognizes_both_orders_without_swallowing_neighboring_markup(self):
        block = critical.build_block('\t', 'body{color:ivory}', '0' * critical.HASH_LEN,
                                     self.hrefs, async_hrefs=self.selected())
        lines = block.splitlines()
        legacy = '\n'.join([lines[-2], *lines[:-2], lines[-1]])
        prefix, suffix = '<head>\n<meta name="before">\n', '\n<script src="after.js"></script></head>'
        for candidate in (legacy, block):
            with self.subTest(order=candidate):
                start, end, indent, hrefs = critical.find_region(prefix + candidate + suffix,
                                                                'fixture.html')
                self.assertEqual((start, end), (len(prefix), len(prefix + candidate)))
                self.assertEqual(indent, '\t')
                self.assertEqual(hrefs, self.hrefs)

    def process_fixture(self, directory, check=False):
        with patch.object(critical, 'ROOT', directory), redirect_stdout(io.StringIO()):
            return critical.process_page('fixture.html', self.sources,
                                         critical.css_class_universe(self.sources), check)

    def write_fixture(self, directory):
        path = Path(directory) / 'fixture.html'
        links = '\n'.join('<link rel="stylesheet" href="%s">' % href for href in self.hrefs)
        path.write_text(self.html.replace('</head>', links + '</head>'))
        return path

    def test_legacy_order_is_stale_and_converts_once_without_css_or_version_changes(self):
        self.sources['css/edition-2027.css'] = '.edition-2027{font:500 80px serif}'
        self.sources['css/edition-personality.css'] = '.edition-2027{font:900 80px Inter}'
        universe = critical.css_class_universe(self.sources)
        css = critical.build_critical_css(self.html, self.sources, universe)
        digest = critical.critical_hash(css, self.sources)
        expected = critical.build_block('  ', css, digest, self.hrefs,
                                        async_hrefs=self.selected())
        lines = expected.splitlines()
        legacy = '\n'.join([lines[-2], *lines[:-2], lines[-1]])
        prefix, suffix = '<html><head>\n', '\n</head><body class="edition-2027"></body></html>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.html'
            path.write_text(prefix + legacy + suffix)
            self.assertFalse(self.process_fixture(directory, check=True)[0])
            self.assertTrue(self.process_fixture(directory)[2])
            self.assertEqual(path.read_text(), prefix + expected + suffix)
            self.assertEqual(critical.DATA_CRITICAL_RE.findall(path.read_text()), [digest])
            self.assertTrue(self.process_fixture(directory, check=True)[0])
            self.assertFalse(self.process_fixture(directory)[2])

    def test_class_change_restores_a_previously_omitted_link_automatically(self):
        self.sources['css/edition-stay.css'] = '.scene-hotel{background:ivory}'
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fixture(directory)
            self.assertTrue(self.process_fixture(directory)[0])
            original = path.read_text()
            href = '/css/edition-stay.css?v=fixture'
            self.assertNotIn(href, original.split('<noscript')[0])
            path.write_text(original.replace('class="edition-2027"',
                                             'class="edition-2027 scene-hotel"'))
            self.assertFalse(self.process_fixture(directory, check=True)[0])
            self.assertTrue(self.process_fixture(directory)[0])
            restored = path.read_text()
            self.assertIn(href, restored.split('<noscript')[0])
            self.assertEqual(critical.find_region(restored, path.name)[3], self.hrefs)
            self.assertTrue(self.process_fixture(directory, check=True)[0])
            self.assertFalse(self.process_fixture(directory)[2])

    def test_freshness_rejects_active_link_drift_without_a_hash_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fixture(directory)
            self.process_fixture(directory)
            original = path.read_text()
            link = re.search(r'<link rel="stylesheet"[^>]+media="print"[^>]*>', original).group(0)
            optional_link = link.replace('/css/fonts.css', '/css/edition-stay.css')
            changes = [
                original.replace(link + '\n', '', 1),
                original.replace(link, link.replace('?v=fixture', '?v=drift'), 1),
                original.replace(link, link.replace('media="print"', 'media="screen"'), 1),
                original.replace(link, link + '\n' + optional_link, 1),
            ]
            for changed in changes:
                with self.subTest(change=changed):
                    self.assertEqual(critical.DATA_CRITICAL_RE.findall(changed),
                                     critical.DATA_CRITICAL_RE.findall(original))
                    path.write_text(changed)
                    self.assertFalse(self.process_fixture(directory, check=True)[0])
                    self.assertTrue(self.process_fixture(directory)[0])
                    self.assertEqual(path.read_text(), original)

    def test_freshness_rejects_incomplete_or_reordered_fallback_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_fixture(directory)
            self.process_fixture(directory)
            original = path.read_text()
            prefix, fallback = original.split('<noscript data-critical-fallback>', 1)
            first = '<link rel="stylesheet" href="%s">' % self.hrefs[0]
            second = '<link rel="stylesheet" href="%s">' % self.hrefs[1]
            for modified in (fallback.replace(first, '', 1),
                             fallback.replace(first + second, second + first, 1)):
                path.write_text(prefix + '<noscript data-critical-fallback>' + modified)
                self.assertFalse(self.process_fixture(directory, check=True)[0])


if __name__ == '__main__':
    unittest.main()
