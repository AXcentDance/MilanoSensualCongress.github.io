"""Regression coverage for requirements consolidated into their owning checker."""
import copy
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_image_seo import image_problems
from check_page_contract import audit_page
import run_all_checks


class CheckerOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.html = (root / 'index.html').read_text()

    def page(self):
        return BeautifulSoup(self.html, 'html.parser')

    def test_current_homepage_passes_the_consolidated_contract(self):
        self.assertEqual(audit_page(self.html, 'index.html'), [])

    def test_required_page_elements_still_reject_missing_and_duplicate_tags(self):
        cases = [
            ('title', 'exactly one head title required'),
            ('meta[name="description"]', 'exactly one nonempty description meta required'),
            ('meta[name="theme-color"]', 'exactly one nonempty theme-color meta required'),
            ('meta[http-equiv="Content-Security-Policy"]', 'exactly one CSP meta required'),
            ('link[rel="canonical"]', 'single canonical or intentional noindex required'),
            ('script[type="speculationrules"]', 'one speculation-rules block required'),
            ('script[src^="/js/site-analytics.js?v="]', 'one shared site-analytics.js loader required'),
            ('script[src^="/js/prefetch-fallback.js?v="]', 'one shared prefetch-fallback.js loader required'),
        ]
        for selector, message in cases:
            for operation in ['remove', 'duplicate']:
                with self.subTest(selector=selector, operation=operation):
                    soup = self.page()
                    tag = soup.select_one(selector)
                    self.assertIsNotNone(tag)
                    if operation == 'remove':
                        tag.decompose()
                    else:
                        tag.insert_after(copy.copy(tag))
                    errors = audit_page(str(soup), 'index.html')
                    self.assertEqual(errors, [message])

    def test_canonical_and_csp_cannot_be_moved_or_duplicated_into_the_body(self):
        for selector, message in [
            ('meta[http-equiv="Content-Security-Policy"]', 'exactly one CSP meta required'),
            ('link[rel="canonical"]', 'single canonical or intentional noindex required'),
        ]:
            for operation in ['move', 'duplicate']:
                with self.subTest(selector=selector, operation=operation):
                    soup = self.page()
                    tag = soup.select_one(selector)
                    soup.body.append(tag.extract() if operation == 'move' else copy.copy(tag))
                    self.assertEqual(audit_page(str(soup), 'index.html'), [message])

    def test_wrong_canonical_and_accidental_noindex_still_fail(self):
        soup = self.page()
        soup.find('link', rel='canonical')['href'] = 'https://milanosensualcongress.com/wrong'
        self.assertIn('canonical must match the clean page URL', audit_page(str(soup), 'index.html'))
        soup = self.page()
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots is None:
            robots = soup.new_tag('meta', attrs={'name': 'robots'})
            soup.head.append(robots)
        robots['content'] = 'noindex'
        self.assertIn('unexpected noindex on public page', audit_page(str(soup), 'index.html'))

    def test_each_google_and_meta_permission_must_be_in_the_correct_csp_directive(self):
        # Explicit preserved requirements: do not import the implementation's map.
        permissions = [
            ('script-src', 'https://www.googletagmanager.com'),
            ('img-src', 'https://*.google-analytics.com'),
            ('img-src', 'https://www.googletagmanager.com'),
            ('connect-src', 'https://*.google-analytics.com'),
            ('connect-src', 'https://*.analytics.google.com'),
            ('connect-src', 'https://www.googletagmanager.com'),
            ('img-src', 'https://www.facebook.com'),
            ('img-src', 'https://connect.facebook.net'),
            ('form-action', 'https://www.facebook.com/tr/'),
            ('connect-src', 'https://www.facebook.com'),
            ('connect-src', 'https://connect.facebook.net'),
            ('connect-src', 'https://dv-c3e594c6d429469e90b54478358619c3.ecs.us-east-1.on.aws'),
            ('connect-src', 'https://bded8a3c6ae-1-1053047382554.us-central1.run.app'),
        ]
        for directive, origin in permissions:
            with self.subTest(directive=directive, origin=origin):
                soup = self.page()
                csp = soup.find('meta', attrs={'http-equiv': 'Content-Security-Policy'})
                directives = [value.split() for value in csp['content'].split(';') if value.strip()]
                sources = next(parts for parts in directives if parts[0] == directive)
                self.assertIn(origin, sources)
                sources.remove(origin)
                # A lookalike host or the right source in the wrong directive must
                # not satisfy this permission through raw substring matching.
                sources.append(origin + '.invalid')
                directives.append(['font-src', origin])
                csp['content'] = '; '.join(' '.join(parts) for parts in directives)
                self.assertEqual(audit_page(str(soup), 'index.html'), [
                    f'CSP {directive} missing verified tracking sources: {origin}',
                ])

    def test_missing_or_empty_csp_content_fails_without_crashing(self):
        for value in [None, '']:
            with self.subTest(value=value):
                soup = self.page()
                csp = soup.find('meta', attrs={'http-equiv': 'Content-Security-Policy'})
                if value is None:
                    del csp['content']
                else:
                    csp['content'] = value
                self.assertEqual(audit_page(str(soup), 'index.html'), ['exactly one CSP meta required'])

    def test_legacy_inline_pixel_still_fails_with_the_shared_loader_present(self):
        soup = self.page()
        script = soup.new_tag('script')
        script.string = 'function initMetaPixel() {}'
        soup.body.append(script)
        self.assertEqual(audit_page(str(soup), 'index.html'), ['legacy inline Meta Pixel initializer is forbidden'])

    def test_image_alt_has_one_owner_and_keeps_decorative_and_name_only_values(self):
        for alt in [None, '', 'Artist name']:
            with self.subTest(alt=alt):
                soup = self.page()
                image = soup.find('img')
                if alt is None:
                    del image['alt']
                else:
                    image['alt'] = alt
                errors = audit_page(str(soup), 'index.html') + image_problems(image)
                self.assertEqual(errors, ['missing alt attribute'] if alt is None else [])

    def test_image_dimensions_remain_required_by_the_page_contract(self):
        for attribute in ['width', 'height']:
            for value in [None, '0', '-1', 'auto']:
                with self.subTest(attribute=attribute, value=value):
                    soup = self.page()
                    image = soup.find('img')
                    if value is None:
                        del image[attribute]
                    else:
                        image[attribute] = value
                    self.assertIn('image missing dimensions: ' + image['src'], audit_page(str(soup), 'index.html'))

    def test_cross_page_duplicate_metadata_still_fails(self):
        html = '<html><head><title>Repeated title</title><meta name="description" content="Repeated description"></head></html>'
        with patch.object(run_all_checks, 'pages', return_value=['one.html', 'two.html']), \
             patch.object(run_all_checks, 'FAILURES', []) as failures, \
             patch('builtins.open', mock_open(read_data=html)):
            run_all_checks.check_metadata_unique()
            self.assertEqual(len(failures), 2)
            self.assertTrue(any('duplicate title' in error for error in failures))
            self.assertTrue(any('duplicate meta description' in error for error in failures))

    def test_metadata_uniqueness_survives_attribute_order_quotes_and_entities(self):
        first = '<html><head><title>Repeated &amp; title</title><meta name="description" content="Repeated description"></head></html>'
        second = "<html><head><title>Repeated &#38; title</title><meta content='Repeated description' name='description'></head></html>"
        with patch.object(run_all_checks, 'pages', return_value=['one.html', 'two.html']), \
             patch.object(run_all_checks, 'FAILURES', []) as failures, \
             patch('builtins.open', side_effect=[io.StringIO(first), io.StringIO(second)]):
            run_all_checks.check_metadata_unique()
            self.assertEqual(failures, [
                'duplicate title in two.html and one.html: "Repeated & title"',
                'duplicate meta description in two.html and one.html: "Repeated description"',
            ])

    def test_missing_metadata_is_reported_only_by_the_page_contract(self):
        soup = self.page()
        soup.title.decompose()
        soup.find('meta', attrs={'name': 'description'}).decompose()
        html = str(soup)
        with patch.object(run_all_checks, 'pages', return_value=['index.html']), \
             patch.object(run_all_checks, 'FAILURES', []) as failures, \
             patch('builtins.open', mock_open(read_data=html)):
            run_all_checks.check_metadata_unique()
            self.assertEqual(failures, [])
        self.assertEqual(audit_page(html, 'index.html'), [
            'exactly one head title required', 'exactly one nonempty description meta required',
        ])

    def test_missing_sitemap_page_still_fails(self):
        tree = run_all_checks.ET.ElementTree(run_all_checks.ET.fromstring(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'))
        with patch.object(run_all_checks, 'pages', return_value=['index.html']), \
             patch.object(run_all_checks, 'FAILURES', []) as failures, \
             patch.object(run_all_checks.ET, 'parse', return_value=tree), \
             patch('builtins.open', mock_open(read_data=self.html)):
            run_all_checks.check_sitemap()
            self.assertEqual(failures, ['sitemap.xml: missing indexable page https://milanosensualcongress.com/'])


if __name__ == '__main__':
    unittest.main()
