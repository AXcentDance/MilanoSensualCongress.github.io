"""Public discovery and intentional noindex must agree across all consumers."""
from contextlib import contextmanager, redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from bs4 import BeautifulSoup
import site_files as policy
from generation_support import GenerationError
import generate_llms_text as llms
import generate_sitemap as sitemap
import generate_md_twins as markdown
import generate_rss as rss
import run_all_checks as checks
import ping_indexnow
import sync_social_meta
from build_site import build_site
from check_page_contract import audit_page
from check_orphans import unreachable_pages


class PagePolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for module, name, value in [
            (llms, 'ROOT_DIR', str(self.root)),
            (llms, 'OUTPUT_FULL', str(self.root / 'llms-full.txt')),
            (llms, 'OUTPUT_SUMMARY', str(self.root / 'llms.txt')),
            (sitemap, 'ROOT_DIR', str(self.root)),
            (markdown, 'ROOT_DIR', str(self.root)),
            (rss, 'ROOT_DIR', str(self.root)),
        ]:
            replacement = patch.object(module, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def page(self, name='index.html', head='', body='Congress information'):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'<html><head><title>{name}</title>{head}</head><body><main>{body}</main></body></html>')
        return target

    @contextmanager
    def in_root(self):
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            yield
        finally:
            os.chdir(previous)

    def test_one_manifest_separates_public_utilities_from_indexable_content(self):
        self.page()
        self.page('404.html', '<meta name="robots" content="noindex">')
        self.page('it/news/new/index.html')
        self.page('news/myindex.html')
        for name in ['.hidden.html', '.agent/private.html', 'output/draft.html',
                     'System/report.html', 'tests/fixture.html', 'news/.draft/test.html',
                     'assets/demo.html', 'images/demo.html', 'fonts/demo.html',
                     'node_modules/demo.html', 'tmp/demo.html']:
            self.page(name)
        self.assertEqual(policy.page_manifest(self.root), [
            {'file': '404.html', 'path': '/404', 'indexable': False},
            {'file': 'index.html', 'path': '/', 'indexable': True},
            {'file': 'it/news/new/index.html', 'path': '/it/news/new/', 'indexable': True},
            {'file': 'news/myindex.html', 'path': '/news/myindex', 'indexable': True},
        ])
        self.assertEqual(markdown.collect_pages(), policy.site_pages(self.root))

    def test_restrictive_directives_cannot_silently_hide_an_unapproved_page(self):
        for head in ['<meta content="NOINDEX, follow" name="RoBoTs">',
                     '<meta name="robots" content="index"><meta name="ROBOTS" content="noindex">',
                     '<meta name="robots" content="none">',
                     '<meta name="googlebot" content="noindex">']:
            with self.subTest(head=head):
                soup = BeautifulSoup(f'<head>{head}</head>', 'html.parser')
                with self.assertRaisesRegex(GenerationError, 'tickets.html: unexpected noindex'):
                    policy.page_is_indexable('tickets.html', soup)

    def test_words_in_content_and_nonrestrictive_values_do_not_hide_pages(self):
        self.page(head='<meta name="description" content="Explaining noindex">'
                  '<meta name="robots" content="max-image-preview: none, index">'
                  '<!-- <meta name="robots" content="noindex"> -->',
                  body='The word noindex and <code>&lt;meta name="robots" content="noindex"&gt;</code>')
        self.assertEqual(policy.indexable_pages(self.root), ['index.html'])

    def test_registry_and_valid_head_directive_are_both_required(self):
        for content in ['<head></head>', '<head><meta name="robots" content="index"></head>',
                        '<head><meta name="googlebot" content="noindex"></head>',
                        '<head></head><body><meta name="robots" content="noindex"></body>']:
            with self.subTest(content=content):
                with self.assertRaisesRegex(GenerationError, 'must retain a head robots noindex'):
                    policy.page_is_indexable('404.html', BeautifulSoup(content, 'html.parser'))
        for content in ['noindex,follow', 'NONE']:
            soup = BeautifulSoup(f'<head><meta content="{content}" name="ROBOTS"></head>', 'html.parser')
            self.assertFalse(policy.page_is_indexable('404.html', soup))

    def test_misplaced_restriction_is_an_error_not_an_indexing_decision(self):
        soup = BeautifulSoup('<head></head><body><meta name="robots" content="noindex"></body>', 'html.parser')
        issues = policy.indexing_issues('tickets.html', soup)
        self.assertIn('unexpected noindex on public page', issues)
        self.assertIn('robots indexing directives must be in the head', issues)

    @patch.dict(policy.NONINDEXED_PAGES, {'confirmation.html': 'Test-only utility'})
    def test_approved_utility_is_excluded_from_exports_and_stale_twin_is_removed(self):
        self.page()
        self.page('confirmation.html', '<meta name="robots" content="index">'
                  '<meta content="noindex" name="ROBOTS">', 'UTILITY CONTENT')
        self.page('output/draft.html', body='DRAFT CONTENT')
        (self.root / 'confirmation.md').write_text(markdown.MARKER + '\nOld utility content')
        (self.root / 'notes.md').write_text('Handwritten note')
        (self.root / 'output/draft.md').write_text(markdown.MARKER + '\nUnrelated draft')
        with redirect_stdout(io.StringIO()), patch.object(sys, 'argv', ['generate_md_twins.py']), \
             patch.object(sitemap, 'get_lastmod', return_value='2026-09-12T12:00:00+02:00'):
            sitemap.generate_sitemap()
            llms.main()
            self.assertEqual(markdown.main(), 0)
        for name in ['llms.txt', 'llms-full.txt', 'sitemap.xml', 'index.md']:
            text = (self.root / name).read_text()
            self.assertNotIn('UTILITY CONTENT', text)
            self.assertNotIn('DRAFT CONTENT', text)
            self.assertNotIn('confirmation', text)
        self.assertFalse((self.root / 'confirmation.md').exists())
        self.assertEqual((self.root / 'notes.md').read_text(), 'Handwritten note')
        self.assertTrue((self.root / 'output/draft.md').exists())
        locs = ET.parse(self.root / 'sitemap.xml').findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        self.assertEqual(len(locs), 1)
        self.assertEqual(len(policy.site_pages(self.root)), 2)

    def test_unapproved_noindex_stops_every_export_before_writes(self):
        self.page()
        self.page('tickets.html', '<meta name="robots" content="noindex">')
        old = {'llms.txt': 'Old summary', 'llms-full.txt': 'Old text',
               'sitemap.xml': 'Old sitemap', 'feed.xml': 'Old feed',
               'index.md': markdown.MARKER + '\nOld twin'}
        for name, content in old.items():
            (self.root / name).write_text(content)
        for generate in [llms.main, sitemap.generate_sitemap, markdown.main, rss.main]:
            with self.subTest(generator=generate.__module__), redirect_stdout(io.StringIO()), \
                 patch.object(sys, 'argv', ['generate.py']):
                with self.assertRaisesRegex(GenerationError, 'tickets.html: unexpected noindex'):
                    generate()
                for name, content in old.items():
                    self.assertEqual((self.root / name).read_text(), content)

    @patch.dict(policy.NONINDEXED_PAGES, {'confirmation.html': 'Test-only utility'})
    def test_page_contract_accepts_registered_utilities_without_relaxing_ticket_rules(self):
        template = (SCRIPTS.parent / '404.html').read_text()
        self.assertEqual(audit_page(template, 'confirmation.html'), [])
        errors = audit_page(template, 'tickets.html')
        self.assertIn('unexpected noindex on public page', errors)
        self.assertIn('one unified JSON-LD graph in head required', errors)
        errors = audit_page(template.replace('noindex', 'index'), 'confirmation.html')
        self.assertIn('approved nonindexed page must retain a head robots noindex directive', errors)

    @patch.dict(policy.NONINDEXED_PAGES, {'news/confirmation.html': 'Test-only utility'})
    def test_feed_selection_excludes_approved_utility_even_when_it_has_article_metadata(self):
        dated = '<script type="application/ld+json">{"datePublished":"2026-09-12"}</script>'
        self.page('news/guide.html', dated)
        self.page('news/confirmation.html', dated + '<meta name="robots" content="noindex">')
        self.page('news/.hidden.html', dated)
        feed = rss.build_feed(rss.FEEDS[0])
        self.assertIn('/news/guide', feed)
        self.assertEqual(feed.count('<item>'), 1)
        self.assertNotIn('confirmation', feed)
        self.assertNotIn('.hidden', feed)
        (self.root / 'news/guide.html').unlink()
        (self.root / 'feed.xml').write_text('Previous feed')
        with self.assertRaisesRegex(GenerationError, 'No indexable dated articles'):
            rss.main()
        self.assertEqual((self.root / 'feed.xml').read_text(), 'Previous feed')

    def test_sitemap_requires_pages_that_only_mention_noindex_and_rejects_extras(self):
        self.page(body='An explanation of noindex')
        self.page('404.html', '<meta name="robots" content="noindex">')
        self.page('output/draft.html')
        sitemap_text = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(
            f'<url><loc>{sitemap.DOMAIN}{path}</loc></url>' for path in ['/404', '/output/draft', '/deleted']) + '</urlset>'
        (self.root / 'sitemap.xml').write_text(sitemap_text)
        with self.in_root(), patch.object(checks, 'pages', return_value=policy.site_pages(self.root)), \
             patch.object(checks, 'FAILURES', []) as failures:
            checks.check_sitemap()
        self.assertIn(f'sitemap.xml: missing indexable page {sitemap.DOMAIN}/', failures)
        self.assertEqual(len(failures), 4)
        self.assertEqual(sum('not an indexable public page' in failure for failure in failures), 3)

    def test_release_keeps_public_utility_html_but_excludes_its_stale_markdown(self):
        self.page()
        self.page('404.html', '<meta name="robots" content="noindex">')
        (self.root / 'index.md').write_text('Public twin')
        (self.root / '404.md').write_text('Stale utility twin')
        destination = self.root / '.quality/release'
        self.assertEqual(build_site(destination, self.root), 3)
        self.assertTrue((destination / '404.html').exists())
        self.assertTrue((destination / 'index.md').exists())
        self.assertFalse((destination / '404.md').exists())

    def test_indexnow_and_social_selection_use_indexable_pages_without_network_calls(self):
        self.page()
        self.page('404.html', '<meta name="robots" content="noindex">')
        self.page('news/myindex.html')
        self.page('output/draft.html')
        selected = lambda: policy.indexable_pages(self.root)
        with patch.object(ping_indexnow, 'indexable_pages', side_effect=selected), \
             patch.object(ping_indexnow.subprocess, 'check_output', return_value='index.html\n404.html\nnews/myindex.html\noutput/draft.html\n'), \
             patch.object(ping_indexnow, 'urlopen', side_effect=AssertionError('No network calls')):
            self.assertEqual(ping_indexnow.changed_urls('previous'),
                             [sitemap.DOMAIN + '/', sitemap.DOMAIN + '/news/myindex'])
        with patch.object(sync_social_meta, 'indexable_pages', side_effect=selected), \
             patch.object(sync_social_meta, 'process') as process, redirect_stdout(io.StringIO()):
            process.return_value = None
            sync_social_meta.main()
            self.assertEqual([call.args[0] for call in process.call_args_list], ['index.html', 'news/myindex.html'])

    def test_orphan_check_keeps_indexable_pages_and_rejects_accidental_noindex(self):
        pages = {'index.html': '<html><body><p>noindex</p></body></html>',
                 '404.html': '<head><meta name="robots" content="noindex"></head>',
                 'guide.html': '<html><body>Guide</body></html>'}
        self.assertEqual(unreachable_pages(pages), ['guide.html'])
        pages['guide.html'] = '<head><meta name="robots" content="noindex"></head>'
        with self.assertRaisesRegex(GenerationError, 'guide.html: unexpected noindex'):
            unreachable_pages(pages)


if __name__ == '__main__':
    unittest.main()
