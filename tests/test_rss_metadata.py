"""RSS uses the page article's original date and replaces both feeds safely."""
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import generate_rss as rss
from generation_support import GenerationError, run_generator


class RssMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'news').mkdir()
        (self.root / 'it' / 'news').mkdir(parents=True)
        setting = patch.object(rss, 'ROOT_DIR', str(self.root))
        setting.start()
        self.addCleanup(setting.stop)
        self.previous = {'feed.xml': b'previous English', 'it/feed.xml': b'previous Italian'}
        for path, content in self.previous.items():
            (self.root / path).write_bytes(content)

    def page(self, path='news/article.html', nodes=None, metadata=None, body='<article>Actual article</article>'):
        if nodes is None:
            nodes = [{'@type': 'BlogPosting', 'datePublished': '2026-06-14T09:00:00+02:00'}]
        if metadata is None:
            metadata = '<TITLE>News &amp; dance</TITLE><META content="Useful &amp; accurate" name="description">'
        source = (f'<html><head>{metadata}<script id="schema"\n TYPE = "application/ld+json">'
                  f'{json.dumps({"@context": "https://schema.org", "@graph": nodes})}</script>'
                  f'</head><body>{body}</body></html>')
        target = self.root / path
        target.write_text(source)
        return target

    def assert_preserved(self):
        for path, content in self.previous.items():
            self.assertEqual((self.root / path).read_bytes(), content)

    def test_formatting_and_nonarticle_dates_do_not_change_the_article_date(self):
        path = self.page(nodes=[
            {'@type': 'DanceEvent', 'datePublished': '2027-01-01T12:00:00Z'},
            {'@type': ['CreativeWork', 'BlogPosting'], 'datePublished': '2026-06-14T09:00:00+02:00'},
        ])
        item = rss.parse_article(path)
        self.assertEqual(item['title'], 'News & dance')
        self.assertEqual(item['description'], 'Useful & accurate')
        self.assertEqual(item['dt'].isoformat(), '2026-06-14T09:00:00+02:00')

    def test_apostrophes_inside_double_quoted_description_are_not_truncated(self):
        item = rss.parse_article(self.page(metadata=(
            '<title>Notizie</title><meta name="description" content="Scopri l\'etichetta del congresso.">')))
        self.assertEqual(item['description'], "Scopri l'etichetta del congresso.")

    def test_legitimate_nonarticle_is_optional_but_unmarked_article_is_an_error(self):
        self.assertIsNone(rss.parse_article(self.page(nodes=[{'@type': 'DanceEvent', 'datePublished': '2026-01-01'}], body='<main>Event</main>')))
        with self.assertRaisesRegex(GenerationError, 'missing an Article/BlogPosting'):
            rss.parse_article(self.page(nodes=[{'@type': 'WebPage'}]))

    def test_array_and_top_level_article_are_supported(self):
        for data in [{'@type': 'Article', 'datePublished': '2026-06-14'},
                     [{'@type': 'NewsArticle', 'datePublished': '2026-06-14'}]]:
            path = self.page()
            text = path.read_text()
            start = text.index('{"@context"')
            end = text.index('</script>', start)
            path.write_text(text[:start] + json.dumps(data) + text[end:])
            self.assertEqual(rss.parse_article(path)['dt'].isoformat(), '2026-06-14T00:00:00+00:00')

    def test_missing_invalid_or_ambiguous_article_metadata_is_reported(self):
        for value in [None, '', 'not a date', '2026-02-30', '2026-01-01T10:00:00']:
            with self.subTest(date=value), self.assertRaisesRegex(GenerationError, 'article.html: invalid article datePublished'):
                rss.parse_article(self.page(nodes=[{'@type': 'Article', 'datePublished': value}]))
        with self.assertRaisesRegex(GenerationError, 'article.html: invalid head JSON-LD'):
            rss.parse_article(self.page(nodes=[{'@type': None}]))
        with self.assertRaisesRegex(GenerationError, 'multiple article entities'):
            rss.parse_article(self.page(nodes=[
                {'@type': 'Article', 'datePublished': '2026-01-01'},
                {'@type': 'Article', 'datePublished': '2026-02-01'}]))
        for metadata, message in [('<meta name="description" content="Good">', 'title is missing'),
                                  ('<title>News</title>', 'one nonempty meta description')]:
            with self.assertRaisesRegex(GenerationError, message):
                rss.parse_article(self.page(metadata=metadata))

    def test_webpage_mainentity_selects_the_primary_article(self):
        path = self.page(nodes=[
            {'@type': 'Article', '@id': '#related', 'datePublished': '2025-01-01'},
            {'@type': 'WebPage', 'mainEntity': {'@id': '#article'}},
            {'@type': 'BlogPosting', '@id': '#article', 'datePublished': '2026-06-14'},
        ])
        self.assertEqual(rss.parse_article(path)['dt'].year, 2026)

    def test_malformed_json_and_invalid_xml_do_not_replace_either_feed(self):
        self.page()
        italian = self.page('it/news/articolo.html')
        for replacement, message in [('{broken JSON', 'invalid head JSON-LD'),
                                     ('', 'generated RSS XML is invalid')]:
            if replacement:
                text = italian.read_text()
                start = text.index('{"@context"')
                end = text.index('</script>', start)
                italian.write_text(text[:start] + replacement + text[end:])
            else:
                self.page('it/news/articolo.html', metadata='<title>Bad\x01text</title><meta name="description" content="Good">')
            errors = io.StringIO()
            with redirect_stderr(errors):
                self.assertEqual(run_generator(rss.main), 1)
            self.assertIn(message, errors.getvalue())
            self.assert_preserved()

    def test_both_feeds_are_valid_and_repeat_generation_is_byte_stable(self):
        self.page()
        self.page('it/news/articolo.html')
        rss.main()
        first = {path: (self.root / path).read_bytes() for path in self.previous}
        rss.main()
        for path, content in first.items():
            self.assertEqual((self.root / path).read_bytes(), content)
            self.assertEqual(len(ET.fromstring(content).findall('./channel/item')), 1)

    def test_second_feed_write_failure_rolls_back_first_feed(self):
        self.page()
        self.page('it/news/articolo.html')
        replace = os.replace

        def fail_italian(source, target):
            if Path(target) == self.root / 'it/feed.xml' and not str(source).endswith('.old'):
                raise OSError('simulated Italian replacement failure')
            return replace(source, target)

        with patch('generation_support.os.replace', side_effect=fail_italian):
            with self.assertRaisesRegex(GenerationError, 'simulated Italian replacement failure'):
                rss.main()
        self.assert_preserved()


if __name__ == '__main__':
    unittest.main()
