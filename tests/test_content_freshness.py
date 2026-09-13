"""Meaningful sitemap dates survive technical edits and fail safely without Git."""
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
from content_freshness import PageRevisions, semantic_fingerprint, stable_url
from generation_support import GenerationError
import generate_sitemap as sitemap


def page(text='Original congress information', *, classes='old', version='1',
         title='Congress', link='/tickets?offer=one', price='159', image='photo.webp'):
    schema = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebPage', '@id': 'https://example.test/#page'},
        {'@type': 'Event', 'offers': {'price': price}, 'image': [f'/images/{image}?v={version}']},
    ]}
    return (f'<html lang="en"><head><title>{title}</title>'
            '<meta content="Useful description" name="description">'
            f'<link rel="stylesheet" href="/style.css?v={version}">'
            f'<style data-critical="{version}">.example {{ color: red; }}</style>'
            f'<script type="application/ld+json">{json.dumps(schema)}</script>'
            f'</head><body><nav>Site menu</nav><main class="{classes}">'
            f'<h1>{text}</h1><a href="{link}">Tickets</a>'
            f'<img src="/images/{image}?v={version}" alt="Dancing couple" width="800">'
            f'<script src="/app.js?v={version}"></script></main><footer>Footer</footer></body></html>')


class SemanticFingerprintTests(unittest.TestCase):
    def test_swapped_labelled_links_and_removed_headings_are_significant(self):
        original = page().replace('</main>', '<a href="/hotel">Hotel</a></main>')
        swapped = original.replace('/tickets?offer=one', '/placeholder').replace('href="/hotel"', 'href="/tickets?offer=one"').replace('/placeholder', '/hotel')
        self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(swapped))
        self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(original.replace('<h1>', '<p>').replace('</h1>', '</p>')))

    def test_icon_and_navigation_labels_remain_attached_to_their_links(self):
        for links in ['<a aria-label="Tickets" href="/tickets"></a><a aria-label="Hotel" href="/hotel"></a>',
                      '<a href="/tickets">Tickets</a><a href="/hotel">Hotel</a>']:
            original = page().replace('<nav>Site menu</nav>', '<nav>' + links + '</nav>')
            swapped = original.replace('href="/tickets"', 'href="/placeholder"').replace('href="/hotel"', 'href="/tickets"').replace('href="/placeholder"', 'href="/hotel"')
            self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(swapped))

    def test_image_background_changes_count_but_colors_do_not(self):
        original = page().replace('color: red', 'color: red; background-image:url(/images/one.webp)')
        self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(original.replace('one.webp', 'two.webp')))
        self.assertEqual(semantic_fingerprint(original), semantic_fingerprint(original.replace('color: red', 'color: green')))

    def test_background_selector_minification_is_not_an_editorial_update(self):
        original = page().replace('.example { color: red; }', '.hero, .banner > img { background: url(/hero.webp); }')
        minified = original.replace('.hero, .banner > img', '.hero,.banner>img')
        self.assertEqual(semantic_fingerprint(original), semantic_fingerprint(minified))
    def media_page(self, media):
        return page().replace('<img src="/images/photo.webp?v=1" alt="Dancing couple" width="800">', media)

    def test_formatting_classes_css_scripts_and_asset_cache_versions_are_ignored(self):
        original = page()
        technical = page(classes='new large bold', version='999')
        technical = technical.replace('<h1>', '\n  <h1>').replace('</h1>', '</h1>\n')
        technical = technical.replace('color: red', 'color: purple').replace('</main>', '<!-- build -->\n</main>')
        self.assertEqual(semantic_fingerprint(original), semantic_fingerprint(technical))

    def test_meaningful_content_metadata_schema_and_links_change_fingerprint(self):
        original = semantic_fingerprint(page())
        for changes in [{'text': 'New confirmed workshop'}, {'title': 'New article title'},
                        {'link': '/tickets?offer=two'}, {'link': '/tickets?v=2'},
                        {'price': '179'}, {'image': 'new-photo.webp'}]:
            with self.subTest(changes=changes):
                self.assertNotEqual(original, semantic_fingerprint(page(**changes)))

    def test_only_asset_version_parameter_is_removed(self):
        self.assertEqual(stable_url('/images/photo.webp?v=2&crop=face'), '/images/photo.webp?crop=face')
        self.assertEqual(stable_url('/tickets?v=2'), '/tickets?v=2')
        self.assertEqual(stable_url('/images/photo.webp?crop=2'), '/images/photo.webp?crop=2')

    def test_json_key_graph_and_type_order_do_not_change_facts(self):
        original = page()
        start = original.index('{"@context"')
        end = original.index('</script>', start)
        graph = json.loads(original[start:end])
        graph['@graph'].reverse()
        rewritten = original[:start] + json.dumps(graph, sort_keys=True, indent=4) + original[end:]
        self.assertEqual(semantic_fingerprint(original), semantic_fingerprint(rewritten))

    def test_picture_and_img_srcset_changes_track_image_identity(self):
        original = self.media_page('<picture><source srcset="/images/mobile_480w.webp 480w, /images/mobile_800w.webp 800w"><img src="/images/photo.webp" srcset="/images/photo_480w.webp 480w" alt="Photo"></picture>')
        updated = original.replace('/images/mobile_', '/images/new-mobile_')
        self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(updated))
        updated = original.replace('/images/photo_480w.webp', '/images/another-photo_480w.webp')
        self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(updated))

    def test_responsive_width_ladders_and_descriptors_do_not_change_identity(self):
        original = self.media_page('<img src="/images/photo.webp?v=1" alt="Photo">')
        responsive = self.media_page('<picture><source srcset="/images/photo_480w.webp?v=2 480w, /images/photo_1200w.webp?v=2 1200w"><img src="/images/photo.webp?v=2" srcset="/images/photo_800w.webp?v=2 800w" sizes="100vw" alt="Photo"></picture>')
        self.assertEqual(semantic_fingerprint(original), semantic_fingerprint(responsive))
        different_ladder = responsive.replace('480w', '600w').replace('1200w', '1600w').replace('100vw', '50vw')
        self.assertEqual(semantic_fingerprint(responsive), semantic_fingerprint(different_ladder))

    def test_deferred_video_sources_are_significant_but_attachment_markup_is_not(self):
        original = self.media_page('<video poster="/images/photo.webp"><source data-src="/images/hero.mp4?v=1"></video>')
        changed = original.replace('hero.mp4', 'new-hero.mp4')
        self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(changed))
        attached = original.replace('data-src=', 'src=').replace('?v=1', '?v=2')
        self.assertEqual(semantic_fingerprint(original), semantic_fingerprint(attached))

    def test_body_navigation_and_submission_destinations_are_significant(self):
        original = page().replace('<nav>Site menu</nav>', '<nav><a href="/tickets">Tickets</a></nav>').replace('<footer>Footer</footer>', '<footer><a href="/contact">Contact</a><form action="/submit"><button formaction="/alternate">Send</button></form></footer>')
        for before, after in [('href="/tickets"', 'href="/new-tickets"'),
                              ('href="/contact"', 'href="/new-contact"'),
                              ('action="/submit"', 'action="/new-submit"'),
                              ('formaction="/alternate"', 'formaction="/new-alternate"')]:
            with self.subTest(destination=before):
                self.assertNotEqual(semantic_fingerprint(original), semantic_fingerprint(original.replace(before, after)))

    def test_footer_copyright_and_repeated_menu_links_do_not_change_freshness(self):
        original = page().replace('<nav>Site menu</nav>', '<nav><a href="/tickets">Tickets</a></nav>').replace('<footer>Footer</footer>', '<footer>Copyright 2026</footer>')
        changed = original.replace('Copyright 2026', 'Copyright 2027').replace('</nav>', '<a href="/tickets">Tickets</a></nav>')
        self.assertEqual(semantic_fingerprint(original), semantic_fingerprint(changed))
        self.assertEqual(semantic_fingerprint(original.replace('<main class="old">', '<div>').replace('</main>', '</div>')),
                         semantic_fingerprint(changed.replace('<main class="old">', '<div>').replace('</main>', '</div>')))


class RevisionRecordTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'scripts').mkdir()
        self.record = self.root / 'scripts/page_revisions.json'
        self.record.write_text('{"version":1,"pages":{}}')
        self.source = self.root / 'index.html'
        self.source.write_text(page())
        (self.root / 'style.css').write_text('.hero {color:red;}')

    def synchronize(self):
        with patch.object(sitemap, 'ROOT_DIR', str(self.root)), redirect_stdout(io.StringIO()):
            sitemap.generate_sitemap()
        return json.loads(self.record.read_text())['pages']['index.html']['lastmod']

    def test_initial_generation_then_technical_edits_keep_the_recorded_date_without_git(self):
        first = self.synchronize()
        self.source.write_text(page(classes='new', version='99'))
        self.assertEqual(self.synchronize(), first)
        self.assertFalse((self.root / '.git').exists())

    def test_new_content_fails_read_only_check_without_changing_outputs(self):
        self.synchronize()
        before = {p: p.read_bytes() for p in [self.record, self.root / 'sitemap.xml']}
        self.source.write_text(page(text='New programme'))
        with patch.object(sitemap, 'ROOT_DIR', str(self.root)):
            with self.assertRaisesRegex(GenerationError, 'not synchronized'):
                sitemap.generate_sitemap(check=True)
        for path, value in before.items():
            self.assertEqual(path.read_bytes(), value)

    def test_sync_updates_a_substantive_revision_once_and_check_detects_stale_xml(self):
        self.synchronize()
        payload = json.loads(self.record.read_text())
        payload['pages']['index.html']['lastmod'] = '2026-01-01T00:00:00+00:00'
        self.record.write_text(json.dumps(payload))
        self.source.write_text(page(text='New confirmed programme'))
        stamp = self.synchronize()
        self.assertNotEqual(stamp, '2026-01-01T00:00:00+00:00')
        self.assertEqual(self.synchronize(), stamp)
        (self.root / 'sitemap.xml').write_text('<obsolete/>')
        with patch.object(sitemap, 'ROOT_DIR', str(self.root)):
            with self.assertRaisesRegex(GenerationError, 'missing or stale'):
                sitemap.generate_sitemap(check=True)
        self.assertEqual((self.root / 'sitemap.xml').read_text(), '<obsolete/>')

    def test_linked_stylesheet_image_change_is_a_new_revision_but_font_change_is_not(self):
        css = self.root / 'style.css'
        css.write_text('.hero {background:url(/one.webp)} @font-face{src:url(/one.woff2)}')
        self.synchronize()
        css.write_text('.hero {background:url(/one.webp)} @font-face{src:url(/two.woff2)}')
        self.assertIsNotNone(PageRevisions(self.root, check=True).lastmod(self.source))
        css.write_text('.hero {background:url(/two.webp)}')
        with self.assertRaisesRegex(GenerationError, 'not synchronized'):
            PageRevisions(self.root, check=True).lastmod(self.source)

    def test_missing_or_invalid_record_never_resets_known_dates(self):
        self.record.unlink()
        with self.assertRaisesRegex(GenerationError, 'restore it from Git'):
            PageRevisions(self.root)
        self.record.write_text('invalid')
        with self.assertRaisesRegex(GenerationError, 'cannot load'):
            PageRevisions(self.root)

    def test_future_date_is_rejected(self):
        self.synchronize()
        payload = json.loads(self.record.read_text())
        payload['pages']['index.html']['lastmod'] = '2099-01-01T00:00:00Z'
        self.record.write_text(json.dumps(payload))
        with self.assertRaisesRegex(GenerationError, 'future'):
            PageRevisions(self.root).lastmod(self.source)

    def test_sitemap_write_failure_rolls_back_revision_record_too(self):
        self.synchronize()
        before = self.record.read_bytes()
        self.source.write_text(page(text='New content'))
        import generation_support
        replace = generation_support.os.replace
        def fail_record(src, target):
            if Path(target).resolve() == self.record.resolve() and Path(src).suffix != '.old':
                raise OSError('disk full')
            return replace(src, target)
        with patch.object(sitemap, 'ROOT_DIR', str(self.root)), patch.object(generation_support.os, 'replace', side_effect=fail_record):
            with self.assertRaisesRegex(GenerationError, 'disk full'):
                sitemap.generate_sitemap()
        self.assertEqual(self.record.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
