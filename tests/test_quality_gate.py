import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from site_files import site_pages
from audit_hreflang import validate_clusters
from check_page_contract import audit_page
from build_site import build_site
from check_image_seo import image_problems
from check_orphans import unreachable_pages
import run_all_checks
import apply_responsive_images as responsive_images


class QualityGateTests(unittest.TestCase):
    def test_nested_italian_images_resolve_and_explicit_lcp_stays_eager(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'it/news').mkdir(parents=True)
            (root / 'images').mkdir()
            (root / 'images/photo.webp').write_bytes(b'fixture')
            page = root / 'it/news/new.html'
            page.write_text('<img src="../../images/photo.webp" fetchpriority="high" loading="lazy" alt="Photo">')
            previous = os.getcwd()
            try:
                os.chdir(root)
                with patch.object(responsive_images, 'dims', return_value=(1000, 800)):
                    responsive_images.process_page('it/news/new.html')
            finally:
                os.chdir(previous)
            image = BeautifulSoup(page.read_text(), 'html.parser').img
            self.assertEqual(image['width'], '1000')
            self.assertEqual(image['loading'], 'eager')
            self.assertEqual(image['fetchpriority'], 'high')

    def test_empty_alt_is_valid_but_omitting_alt_is_not(self):
        images = BeautifulSoup('<img src="decoration.webp" alt=""><img src="content.webp">', 'html.parser').find_all('img')
        self.assertEqual(image_problems(images[0]), [])
        self.assertEqual(image_problems(images[1]), ['missing alt attribute'])

    def test_an_isolated_translation_pair_is_not_reachable(self):
        pages = {'index.html': '<html><body>Home</body></html>',
                 'news/new.html': '<html><head><link hreflang="it" href="/it/news/new"></head><body><a href="/it/news/new">IT</a></body></html>',
                 'it/news/new.html': '<html><body><a href="/news/new">EN</a></body></html>'}
        self.assertEqual(unreachable_pages(pages), ['it/news/new.html', 'news/new.html'])
        pages['index.html'] = '<html><body><a href="/news/new">Read the article</a></body></html>'
        self.assertEqual(unreachable_pages(pages), [])

    def test_release_preserves_public_bytes_and_excludes_project_internals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory, 'source')
            public = ['index.html', 'index.md', 'it/new.html', 'css/site.css',
                      'images/photo.webp', '.well-known/security.txt', '.nojekyll']
            private = ['AGENTS.md', '.agent/rules/delivery.md', '.quality/report.html',
                       'System/report.md', 'node_modules/example.html', 'package.json']
            for name in public + private:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                content = f'<html><body>{name}</body></html>' if name.endswith('.html') else name
                file.write_bytes(content.encode())
            output = Path(directory, 'release')
            self.assertEqual(build_site(output, root), len(public))
            for name in public:
                self.assertEqual((output / name).read_bytes(), (root / name).read_bytes())
            for name in private:
                self.assertFalse((output / name).exists())
            with self.assertRaises(ValueError):
                build_site(root, root)

    def test_new_nested_pages_are_discovered_but_reports_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['index.html', 'news/new/topic.html', '.quality/report.html',
                         'node_modules/demo.html', 'System/report.html', 'tests/fixture.html']:
                file = Path(directory, name)
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('<html></html>')
            self.assertEqual(site_pages(directory), ['index.html', 'news/new/topic.html'])

    def test_release_rejects_a_link_to_a_file_omitted_from_the_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory, 'source')
            root.mkdir()
            (root / 'index.html').write_text('<a href="/download.pdf">Download</a>')
            (root / 'download.pdf').write_bytes(b'Present in checkout, outside the public file list')
            with self.assertRaisesRegex(ValueError, 'Missing packaged resources.*'):
                build_site(Path(directory, 'release'), root)

    def test_a_return_link_to_the_wrong_english_page_is_not_reciprocal(self):
        links = {'en': 'https://site/a', 'it': 'https://site/it/a', 'x-default': 'https://site/a'}
        pages = {'a.html': {'canonical': links['en'], 'links': links},
                 'it/a.html': {'canonical': links['it'], 'links': dict(links)}}
        self.assertEqual(validate_clusters(pages), [])
        pages['it/a.html']['links']['en'] = 'https://site/b'
        self.assertTrue(validate_clusters(pages))

    def test_missing_menu_target_fails_the_contract(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / 'index.html').read_text()
        self.assertEqual(audit_page(html, 'index.html'), [])
        html = html.replace('id="mobile-menu"', 'id="different-menu"')
        self.assertIn('aria-controls points to a missing element: mobile-menu', audit_page(html, 'index.html'))

    def test_a_success_message_cannot_mask_a_failed_process(self):
        with patch.object(run_all_checks, 'CHECKERS', [(['example.py'], 'success')]), \
             patch.object(run_all_checks, 'FAILURES', []) as failures, \
             patch('builtins.print'), \
             patch.object(run_all_checks.subprocess, 'run', return_value=CompletedProcess([], 1, 'success', 'failed')):
            run_all_checks.run_absorbed_checkers()
            self.assertEqual(len(failures), 1)


if __name__ == '__main__':
    unittest.main()
