"""Markdown generation preserves ownership and complete output sets."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import generate_md_twins as markdown
import generation_support as support


class MarkdownGenerationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        setting = patch.object(markdown, 'ROOT_DIR', str(self.root))
        setting.start()
        self.addCleanup(setting.stop)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def page(self, name='index.html', text='Current congress information'):
        return self.put(name, '<html><head><title>Congress</title></head>'
                        f'<body><main><h1>{text}</h1></main></body></html>')

    def twin(self, name, text='Previous generated content'):
        return self.put(name, markdown.MARKER + '\n' + text + '\n')

    def run_generation(self, check=False):
        stdout, stderr = io.StringIO(), io.StringIO()
        arguments = ['generate_md_twins.py'] + (['--check'] if check else [])
        with patch.object(sys, 'argv', arguments), redirect_stdout(stdout), redirect_stderr(stderr):
            status = markdown.main()
        return status, stdout.getvalue(), stderr.getvalue()

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def test_required_handwritten_collision_fails_read_only_check(self):
        self.page()
        self.put('index.md', 'Handwritten content must survive\n')
        before = self.snapshot()
        status, stdout, stderr = self.run_generation(check=True)
        self.assertEqual(status, 1)
        self.assertIn('index.md', stdout + stderr)
        self.assertIn('marker', stdout + stderr)
        self.assertNotIn('md twins up to date', stdout)
        self.assertEqual(self.snapshot(), before)

    def test_collision_blocks_other_updates_and_orphan_removals(self):
        self.page('a.html')
        self.twin('a.md')
        self.page('z.html')
        self.put('z.md', 'Handwritten content must survive\n')
        self.twin('orphan.md')
        before = self.snapshot()
        status, stdout, stderr = self.run_generation()
        self.assertEqual(status, 1)
        self.assertIn('z.md', stdout + stderr)
        self.assertEqual(self.snapshot(), before)

    def test_empty_discovery_cannot_delete_previous_twins(self):
        self.twin('index.md')
        before = self.snapshot()
        for check in (False, True):
            with self.subTest(check=check):
                with self.assertRaisesRegex(support.GenerationError, 'No indexable HTML pages'):
                    self.run_generation(check=check)
                self.assertEqual(self.snapshot(), before)

    def test_later_staging_failure_preserves_all_previous_twins(self):
        for name in ('a', 'b'):
            self.page(name + '.html')
            self.twin(name + '.md')
        before = self.snapshot()
        original = Path.write_text

        def fail(path, *args, **kwargs):
            if path.name == 'b.md' and path.parent.name.startswith('.generation-'):
                raise OSError('simulated full disk')
            return original(path, *args, **kwargs)

        with patch.object(Path, 'write_text', fail):
            with self.assertRaisesRegex(support.GenerationError, 'simulated full disk'):
                self.run_generation()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.root.rglob('.generation-*')))

    def test_later_replacement_failure_restores_earlier_twin(self):
        for name in ('a', 'b'):
            self.page(name + '.html')
            self.twin(name + '.md')
        before = self.snapshot()
        original = support.os.replace

        def fail(source, target):
            if Path(target) == self.root / 'b.md' and Path(source).name == 'b.md':
                raise OSError('simulated replacement failure')
            return original(source, target)

        with patch.object(support.os, 'replace', side_effect=fail):
            with self.assertRaisesRegex(support.GenerationError, 'simulated replacement failure'):
                self.run_generation()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.root.rglob('.generation-*')))

    def test_orphan_removal_failure_restores_updates_and_prior_removals(self):
        self.page()
        self.twin('index.md')
        self.twin('a-orphan.md')
        failed = self.twin('z-orphan.md')
        before = self.snapshot()
        original = Path.unlink

        def fail(path, *args, **kwargs):
            if path == failed:
                raise OSError('simulated removal failure')
            return original(path, *args, **kwargs)

        with patch.object(Path, 'unlink', fail):
            with self.assertRaisesRegex(support.GenerationError, 'simulated removal failure'):
                self.run_generation()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.root.rglob('.generation-*')))

    def test_success_writes_exact_rendering_removes_orphan_and_keeps_notes(self):
        source = self.page()
        expected = markdown.build_twin('index.html', source.read_text(encoding='utf-8'))
        self.twin('orphan.md')
        notes = self.put('notes.md', 'Handwritten notes\n')
        status, stdout, _ = self.run_generation()
        self.assertEqual(status, 0)
        self.assertEqual((self.root / 'index.md').read_text(encoding='utf-8'), expected)
        self.assertFalse((self.root / 'orphan.md').exists())
        self.assertEqual(notes.read_text(encoding='utf-8'), 'Handwritten notes\n')
        self.assertIn('wrote index.md', stdout)
        self.assertIn('deleted orphan orphan.md', stdout)
        self.assertIn('1 written, 0 unchanged, 1 orphan(s) deleted, 0 skipped', stdout)

    def test_successful_check_and_unchanged_write_preserve_file_timestamps(self):
        self.page()
        self.run_generation()
        target = self.root / 'index.md'
        before = (target.read_bytes(), target.stat().st_mtime_ns)
        for check in (True, False):
            with self.subTest(check=check):
                self.assertEqual(self.run_generation(check=check)[0], 0)
                self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)


class MarkdownLinkTests(unittest.TestCase):
    def test_internal_query_parameters_survive_clean_url_conversion(self):
        converter = markdown.PageConverter('news/article.html')
        cases = {
            '/hotel?view=second#booking': '/hotel?view=second#booking',
            '/hotel.html?view=second#booking': '/hotel?view=second#booking',
            '../tickets.html?offer=one&quantity=2': '/tickets?offer=one&quantity=2',
            '?view=second#booking': '/news/article?view=second#booking',
            'https://milanosensualcongress.com/hotel.html?view=second': '/hotel?view=second',
            'https://www.milanosensualcongress.com/it/index.html?campaign=a%2Bb': '/it/?campaign=a%2Bb',
            '/tickets?item=a&item=b&empty=&flag': '/tickets?item=a&item=b&empty=&flag',
        }
        for href, suffix in cases.items():
            with self.subTest(href=href):
                self.assertEqual(converter.resolve_href(href), markdown.BASE_URL + suffix)

    def test_fragment_only_external_and_contact_links_keep_existing_behavior(self):
        converter = markdown.PageConverter('it/news/articolo.html')
        cases = {
            '#booking': markdown.BASE_URL + '/it/news/articolo#booking',
            '../hotel.html#booking': markdown.BASE_URL + '/it/hotel#booking',
            'https://example.test/path.html?item=one#booking': 'https://example.test/path.html?item=one#booking',
            '//example.test/path.html?item=one': '//example.test/path.html?item=one',
            'mailto:info@example.test?subject=Congress': 'mailto:info@example.test?subject=Congress',
            'tel:+39012345': 'tel:+39012345',
            'javascript:void(0)': None,
            '': None,
        }
        for href, expected in cases.items():
            with self.subTest(href=href):
                self.assertEqual(converter.resolve_href(href), expected)


class MarkdownBlockCharacterizationTests(unittest.TestCase):
    def test_containers_and_unknown_wrappers_preserve_existing_rendering(self):
        cases = [
            ('<div>Plain <strong>bold</strong> text</div>', ['Plain **bold** text']),
            ('<span>Inline <em>label</em></span>', ['Inline *label*']),
            ('<msc-card>Custom <a href="/tickets.html">tickets</a></msc-card>',
             ['Custom [tickets](https://milanosensualcongress.com/tickets)']),
            ('<section><h2>Guide</h2><div><p>One</p><p>Two</p></div></section>',
             ['### Guide', 'One', 'Two']),
            ('<msc-card><p>First</p><div><p>Second</p></div></msc-card>', ['First', 'Second']),
            ('<ul><li>First <strong>choice</strong><ul><li>Nested</li></ul></li><li>Second</li></ul>',
             ['- First\n  **choice**\n    - Nested\n- Second']),
            ('<div aria-hidden="true">Hidden</div><aside><span>Visible</span></aside>', ['Visible']),
            ('<blockquote><p>Quoted <em>text</em></p></blockquote><hr>', ['> Quoted *text*', '---']),
        ]
        for markup, expected in cases:
            with self.subTest(markup=markup):
                main = markdown.BeautifulSoup('<main>' + markup + '</main>', 'html.parser').main
                blocks = []
                markdown.PageConverter('news/article.html').blocks(main, blocks)
                self.assertEqual(blocks, expected)


if __name__ == '__main__':
    unittest.main()
