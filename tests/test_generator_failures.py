"""Generation must be complete or fail without discarding previous outputs."""
from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import generate_llms_text as llms
import generate_sitemap as sitemap
import generation_support as support
import site_files


class GeneratorFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.previous = {
            'llms-full.txt': b'Previous full content\n',
            'llms.txt': b'Previous summary\n',
            'sitemap.xml': b'Previous sitemap\n',
        }
        for name, data in self.previous.items():
            (self.root / name).write_bytes(data)
        for module, name, value in [
            (llms, 'ROOT_DIR', str(self.root)),
            (llms, 'OUTPUT_FULL', str(self.root / 'llms-full.txt')),
            (llms, 'OUTPUT_SUMMARY', str(self.root / 'llms.txt')),
            (sitemap, 'ROOT_DIR', str(self.root)),
        ]:
            replacement = patch.object(module, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        dates = patch.object(sitemap, 'get_lastmod', return_value='2026-09-12T12:00:00+02:00')
        dates.start()
        self.addCleanup(dates.stop)

    def add_page(self, path='index.html', title='Congress', head='', body='<main>Event information</main>'):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'<html><head><title>{title}</title>{head}</head><body>{body}</body></html>', encoding='utf-8')
        return target

    def run_generation(self, generate):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = support.run_generator(generate)
        return status, stdout.getvalue(), stderr.getvalue()

    def assert_preserved(self):
        for name, data in self.previous.items():
            self.assertEqual((self.root / name).read_bytes(), data, name)

    def assert_failed(self, generate, detail):
        status, stdout, stderr = self.run_generation(generate)
        self.assertEqual(status, 1)
        self.assertIn(detail, stderr)
        self.assertNotIn('Successfully generated', stdout)
        self.assertNotIn('Sitemap generated at', stdout)
        self.assert_preserved()

    def copy_cli_scripts(self):
        directory = self.root / 'scripts'
        directory.mkdir(exist_ok=True)
        for name in ['generate_llms_text.py', 'generate_sitemap.py', 'generation_support.py', 'site_files.py']:
            shutil.copy2(SCRIPTS / name, directory / name)
        shutil.copy2(SCRIPTS.parent / 'requirements-dev.txt', self.root / 'requirements-dev.txt')
        return directory

    def test_missing_parser_exits_with_install_command_and_preserves_outputs(self):
        self.add_page()
        scripts = self.copy_cli_scripts()
        (scripts / 'bs4.py').write_text('raise ImportError("simulated missing parser")\n')
        for name in ['generate_llms_text.py', 'generate_sitemap.py']:
            with self.subTest(script=name):
                result = subprocess.run([sys.executable, str(scripts / name)], cwd=self.root, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Beautiful Soup is required', result.stderr)
                self.assertIn('-m pip install -r', result.stderr)
                self.assertIn(str(self.root / 'requirements-dev.txt'), result.stderr)
                self.assert_preserved()

    def test_unreadable_page_cli_reports_its_path_and_never_reports_success(self):
        self.add_page()
        broken = self.root / 'broken.html'
        broken.write_bytes(b'\xff')
        scripts = self.copy_cli_scripts()
        for name in ['generate_llms_text.py', 'generate_sitemap.py']:
            with self.subTest(script=name):
                result = subprocess.run([sys.executable, str(scripts / name)], cwd=self.root, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('broken.html', result.stderr)
                self.assertNotIn('Successfully generated', result.stdout)
                self.assertNotIn('Sitemap generated at', result.stdout)
                self.assert_preserved()

    def test_parser_failure_is_fatal_and_names_the_input(self):
        self.add_page()
        with patch.object(support, 'BeautifulSoup', side_effect=RuntimeError('parser failed')):
            for generate in [llms.main, sitemap.generate_sitemap]:
                self.assert_failed(generate, 'index.html: parser failed')

    def test_empty_input_and_empty_html_cannot_replace_existing_outputs(self):
        for generate in [llms.main, sitemap.generate_sitemap]:
            self.assert_failed(generate, 'No indexable HTML pages')
        (self.root / 'index.html').write_text('  \n')
        for generate in [llms.main, sitemap.generate_sitemap]:
            self.assert_failed(generate, 'HTML file is empty')

    def test_directory_scan_failure_is_fatal(self):
        def fail_scan(root, onerror):
            onerror(PermissionError(13, 'Permission denied', str(self.root / 'it')))
            return []
        with patch.object(os, 'walk', side_effect=fail_scan):
            for generate in [llms.main, sitemap.generate_sitemap]:
                self.assert_failed(generate, 'Cannot scan input directory')

    @patch.dict(site_files.NONINDEXED_PAGES, {'confirmation.html': 'Test-only approved confirmation'})
    def test_valid_optional_omissions_and_noindex_are_preserved(self):
        self.add_page()
        self.add_page('it/index.html', title='Congresso', body='<main>Informazioni</main>')
        # No title on an excluded utility page is irrelevant to LLM extraction.
        self.add_page('confirmation.html', title='', head=(' ' * 9000) + '<meta content="noindex,follow" name="robots">', body='EXCLUDED CONTENT')
        ignored = self.root / '.agent' / 'private.html'
        ignored.parent.mkdir()
        ignored.write_bytes(b'\xff')
        for generate in [llms.main, sitemap.generate_sitemap]:
            status, _, stderr = self.run_generation(generate)
            self.assertEqual((status, stderr), (0, ''))
        full = (self.root / 'llms-full.txt').read_text()
        self.assertIn('# Total Pages: 2', full)
        self.assertIn('Informazioni', full)
        self.assertNotIn('EXCLUDED CONTENT', full)
        self.assertNotIn('Description:', full)
        xml = ET.parse(self.root / 'sitemap.xml')
        self.assertEqual(len(xml.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')), 2)
        self.assertEqual(xml.findall('.//{http://www.google.com/schemas/sitemap-image/1.1}image'), [])

    def test_sitemap_keeps_images_empty_alt_and_localized_language_links(self):
        href = sitemap.DOMAIN + '/it/informazioni?a=1&b=2'
        self.add_page(head=f'<link rel="alternate" hreflang="it" href="{href}">',
                      body='<main><img src="images/artist.webp" alt="Artist &amp; partner"><img src="images/decoration.webp" alt=""></main>')
        status, _, stderr = self.run_generation(sitemap.generate_sitemap)
        self.assertEqual((status, stderr), (0, ''))
        xml = ET.parse(self.root / 'sitemap.xml')
        link = xml.find('.//{http://www.w3.org/1999/xhtml}link')
        self.assertEqual(link.get('href'), href)
        images = xml.findall('.//{http://www.google.com/schemas/sitemap-image/1.1}image')
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0].findtext('{http://www.google.com/schemas/sitemap-image/1.1}title'), 'Artist & partner')
        self.assertIsNone(images[1].find('{http://www.google.com/schemas/sitemap-image/1.1}title'))

    def test_sitemap_extraction_helpers_propagate_errors_with_the_page_name(self):
        soup = Mock()
        soup.find_all.side_effect = RuntimeError('extraction failed')
        for extract in [sitemap.get_page_images, sitemap.get_hreflang_links]:
            with self.subTest(extract=extract.__name__):
                with self.assertRaisesRegex(support.GenerationError, 'article.html: extraction failed'):
                    extract('article.html', soup)

    def test_sitemap_extraction_failure_cannot_write_a_reduced_sitemap(self):
        self.add_page()
        for function in ['get_page_images', 'get_hreflang_links']:
            with self.subTest(function=function), patch.object(sitemap, function, side_effect=support.GenerationError('index.html: extraction failed')):
                self.assert_failed(sitemap.generate_sitemap, 'index.html: extraction failed')

    def test_invalid_generated_xml_preserves_previous_sitemap(self):
        self.add_page(body='<main><img src="images/photo.webp" alt="Invalid\x01text"></main>')
        self.assert_failed(sitemap.generate_sitemap, 'generated XML is invalid')

    def test_required_llm_title_and_summary_failure_preserve_both_outputs(self):
        self.add_page(title='')
        self.assert_failed(llms.main, 'index.html: page title is missing or empty')
        self.add_page()
        with patch.object(llms, 'generate_llms_summary', side_effect=ValueError('summary failed')):
            self.assert_failed(llms.main, 'summary failed')
        with patch.object(llms, 'generate_llms_summary', return_value=''):
            self.assert_failed(llms.main, 'generated output is empty or invalid')

    def test_staging_failure_preserves_both_llm_outputs(self):
        self.add_page()
        original = Path.write_text
        def fail_summary(path, *args, **kwargs):
            if path.name == 'llms.txt' and path.parent.name.startswith('.generation-'):
                raise OSError('simulated full disk')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'write_text', fail_summary):
            self.assert_failed(llms.main, 'simulated full disk')
        self.assertEqual(list(self.root.glob('.generation-*')), [])

    def test_second_replacement_failure_rolls_back_the_first_llm_file(self):
        self.add_page()
        original = os.replace
        def fail_summary(source, target):
            if Path(target).name == 'llms.txt' and Path(source).name == 'llms.txt':
                raise OSError('simulated replacement failure')
            return original(source, target)
        with patch.object(os, 'replace', side_effect=fail_summary):
            self.assert_failed(llms.main, 'Previous outputs are unchanged')
        self.assertEqual(list(self.root.glob('.generation-*')), [])

    def test_rollback_removes_new_files_when_there_were_no_previous_outputs(self):
        self.add_page()
        for name in ['llms.txt', 'llms-full.txt']:
            (self.root / name).unlink()
        original = os.replace
        def fail_summary(source, target):
            if Path(target).name == 'llms.txt':
                raise OSError('simulated replacement failure')
            return original(source, target)
        with patch.object(os, 'replace', side_effect=fail_summary):
            self.assertEqual(self.run_generation(llms.main)[0], 1)
        self.assertFalse((self.root / 'llms.txt').exists())
        self.assertFalse((self.root / 'llms-full.txt').exists())

    def test_failed_rollback_retains_recovery_files_and_reports_their_location(self):
        self.add_page()
        original = os.replace
        def fail_replacement_and_rollback(source, target):
            if Path(target).name == 'llms.txt' or Path(source).name.endswith('.old'):
                raise OSError('simulated filesystem failure')
            return original(source, target)
        with patch.object(os, 'replace', side_effect=fail_replacement_and_rollback):
            status, stdout, stderr = self.run_generation(llms.main)
        self.assertEqual(status, 1)
        self.assertNotIn('Successfully generated', stdout)
        self.assertIn('Rollback failed', stderr)
        self.assertNotIn('Previous outputs are unchanged', stderr)
        recovery = list(self.root.glob('.generation-*'))
        self.assertEqual(len(recovery), 1)
        self.assertIn(str(recovery[0]), stderr)
        self.assertEqual((recovery[0] / 'llms-full.txt.old').read_bytes(), self.previous['llms-full.txt'])
        self.assertEqual((self.root / 'llms.txt').read_bytes(), self.previous['llms.txt'])


if __name__ == '__main__':
    unittest.main()
