"""Keep the confirmed next edition distinct from retained sales references."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_event_facts
import edition_facts
import generate_llms_text as llms
from generation_support import GenerationError
from congress_test_fixtures import write_homepages


class EditionFactsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_homepages(self.root)
        self.data = {
            'edition': 2027, 'name': 'Milano Sensual Congress 2027',
            'eventId': 'https://milanosensualcongress.com/#event-2027',
            'startDate': '2027-11-19', 'endDate': '2027-11-21',
            'timezone': 'Europe/Rome', 'datePrecision': 'day',
            'venue': {'name': 'Devero Hotel', 'streetAddress': 'Largo Kennedy, 1',
                      'addressLocality': 'Cavenago di Brianza', 'postalCode': '20873',
                      'addressRegion': 'MB', 'addressCountry': 'IT'},
            'status': {'dates': 'confirmed', 'venue': 'confirmed', 'times': 'unannounced',
                       'tickets': 'unannounced', 'lineup': 'preview'},
        }
        self.source = self.root / 'data/editions/2027.json'
        self.source.parent.mkdir(parents=True)
        self.write_data()
        for page, language in [('index.html', 'en'), ('it/index.html', 'it')]:
            soup = BeautifulSoup((self.root / page).read_text(), 'html.parser')
            script = soup.select_one('script[type="application/ld+json"]')
            graph = json.loads(script.string)
            canonical = 'https://milanosensualcongress.com' + ('/it/' if language == 'it' else '/')
            graph['@graph'] += [edition_facts.schema_event(self.data, language), {
                '@type': 'WebPage', '@id': canonical + '#webpage',
                'mainEntity': {'@id': self.data['eventId']},
            }]
            script.string = json.dumps(graph)
            soup.main.append(BeautifulSoup('<div id="edition-facts">Devero Hotel · '
                '<time datetime="2027-11-19">19</time>–'
                '<time datetime="2027-11-21">21 November 2027</time></div>', 'html.parser'))
            (self.root / page).write_text(str(soup))

    def write_data(self):
        self.source.write_text(json.dumps(self.data))

    def mutate_graph(self, page, change):
        target = self.root / page
        soup = BeautifulSoup(target.read_text(), 'html.parser')
        script = soup.select_one('script[type="application/ld+json"]')
        graph = json.loads(script.string)
        change(graph['@graph'])
        script.string = json.dumps(graph)
        target.write_text(str(soup))

    def announced_node(self, graph):
        return next(node for node in graph if node.get('@id') == self.data['eventId'])

    def check(self):
        with redirect_stdout(io.StringIO()):
            check_event_facts.check(self.root)

    def test_both_editions_validate_without_rewriting_sources(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.check()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_date_and_venue_schema_drift_fail_in_either_language(self):
        for page, field, value in [('index.html', 'startDate', '2027-11-20'),
                                   ('it/index.html', 'endDate', '2027-11-22'),
                                   ('it/index.html', 'location', {'name': 'Another hotel'})]:
            with self.subTest(page=page, field=field):
                original = (self.root / page).read_bytes()
                self.mutate_graph(page, lambda graph: self.announced_node(graph).update({field: value}))
                with self.assertRaisesRegex(GenerationError, f'announced edition {field} disagrees'):
                    self.check()
                (self.root / page).write_bytes(original)

    def test_unannounced_offers_and_performers_cannot_leak_into_2027(self):
        for field in ('offers', 'performer', 'subEvent'):
            with self.subTest(field=field):
                original = (self.root / 'index.html').read_bytes()
                self.mutate_graph('index.html', lambda graph: self.announced_node(graph).update({field: []}))
                with self.assertRaisesRegex(GenerationError, 'must not imply confirmed ' + field):
                    self.check()
                (self.root / 'index.html').write_bytes(original)

    def test_retained_event_consistency_is_still_checked(self):
        self.mutate_graph('it/index.html', lambda graph: graph[0].update(endDate='2030-06-03T22:00:00+02:00'))
        with self.assertRaisesRegex(GenerationError, 'congress endDate disagrees'):
            self.check()

    def test_homepage_cannot_keep_legacy_event_as_primary(self):
        self.mutate_graph('it/index.html', lambda graph: graph[-1].update(
            mainEntity={'@id': 'https://milanosensualcongress.com/#event'}))
        with self.assertRaisesRegex(GenerationError, 'mainEntity must identify the announced edition'):
            self.check()

    def test_visible_date_venue_and_visibility_drift_fail(self):
        page = self.root / 'it/index.html'
        original = page.read_text()
        for before, after, detail in [
            ('datetime="2027-11-19"', 'datetime="2027-11-20"', 'visible edition dates'),
            ('>Devero Hotel', '>Another hotel', 'visible edition venue/year'),
            ('id="edition-facts"', 'id="edition-facts" hidden', 'must remain visible'),
            ('id="edition-facts"', 'id="edition-facts" style="display: none"', 'must remain visible'),
        ]:
            with self.subTest(detail=detail):
                page.write_text(original.replace(before, after))
                with self.assertRaisesRegex(GenerationError, detail):
                    self.check()
        page.write_text(original)

    def test_missing_announcement_definition_and_source_fail(self):
        self.mutate_graph('it/index.html', lambda graph: graph.remove(self.announced_node(graph)))
        with self.assertRaisesRegex(GenerationError, 'expected one announced-edition'):
            self.check()
        self.source.unlink()
        with self.assertRaisesRegex(GenerationError, 'missing source'):
            self.check()

    def test_bad_source_dates_precision_and_confirmation_fail(self):
        for field, value, detail in [
            ('startDate', '2027-02-30', 'invalid edition dates'),
            ('startDate', '2027-11-19T18:00:00+01:00', 'without an invented time'),
            ('endDate', '2027-11-18', 'dates must be ordered'),
            ('endDate', '2028-11-21', 'announced edition year'),
            ('timezone', 'UTC', 'timezone must be'),
            ('status', {'dates': 'unannounced'}, 'status.dates must be'),
        ]:
            with self.subTest(field=field, value=value):
                original = deepcopy(self.data)
                self.data[field] = value
                self.write_data()
                with self.assertRaisesRegex(GenerationError, detail):
                    edition_facts.load_announced_edition(self.root)
                self.data = original
        self.write_data()

    def add_early_bird(self):
        self.data['earlyBird'] = {
            'endsOn': '2026-12-30', 'datePrecision': 'day', 'timezone': 'Europe/Rome',
            'countdownDeadline': '2026-12-31T00:00:00+01:00',
        }
        self.write_data()
        for page in ('index.html', 'it/index.html'):
            target = self.root / page
            soup = BeautifulSoup(target.read_text(), 'html.parser')
            soup.main.append(BeautifulSoup('<section><h2>Early bird</h2>'
                '<p data-countdown-status>Ends <time datetime="2026-12-30">30 December 2026</time></p>'
                '<div data-early-bird-countdown data-deadline="2026-12-31T00:00:00+01:00"></div>'
                '</section>', 'html.parser'))
            target.write_text(str(soup))

    def test_early_bird_final_day_and_bilingual_countdown_validate_without_rewriting(self):
        self.add_early_bird()
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.check()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_early_bird_deadline_uses_next_midnight_and_italian_seasonal_offset(self):
        self.add_early_bird()
        for ends_on, deadline in [('2026-12-30', '2026-12-31T00:00:00+01:00'),
                                  ('2026-06-30', '2026-07-01T00:00:00+02:00'),
                                  ('2026-03-29', '2026-03-30T00:00:00+02:00'),
                                  ('2026-12-31', '2027-01-01T00:00:00+01:00')]:
            with self.subTest(ends_on=ends_on):
                self.data['earlyBird'].update(endsOn=ends_on, countdownDeadline=deadline)
                self.write_data()
                self.assertEqual(edition_facts.load_announced_edition(self.root)['earlyBird']['countdownDeadline'],
                                 deadline)

    def test_invalid_early_bird_fact_and_invented_cutoff_fail(self):
        self.add_early_bird()
        original = deepcopy(self.data['earlyBird'])
        for field, value, detail in [
            ('endsOn', '2026-02-30', 'invalid earlyBird date'),
            ('endsOn', '2026-12-30T18:00:00+01:00', 'calendar date'),
            ('endsOn', None, 'calendar date'),
            ('datePrecision', 'second', 'earlyBird.datePrecision'),
            ('timezone', 'UTC', 'earlyBird.timezone'),
            ('countdownDeadline', '2026-12-30T23:00:00+01:00', 'following midnight'),
            ('countdownDeadline', '2026-12-31T00:00:00+02:00', 'following midnight'),
            ('countdownDeadline', '2026-12-31T00:00:00', 'following midnight'),
        ]:
            with self.subTest(field=field, value=value):
                self.data['earlyBird'] = {**original, field: value}
                self.write_data()
                with self.assertRaisesRegex(GenerationError, detail):
                    edition_facts.load_announced_edition(self.root)
        self.data['earlyBird'] = None
        self.write_data()
        with self.assertRaisesRegex(GenerationError, 'earlyBird must be an object'):
            edition_facts.load_announced_edition(self.root)

    def test_early_bird_timer_and_visible_final_date_cannot_drift_in_either_language(self):
        self.add_early_bird()
        for page in ('index.html', 'it/index.html'):
            target = self.root / page
            original = target.read_text()
            for change, detail in [
                (lambda soup: soup.select_one('[data-early-bird-countdown]').decompose(),
                 'expected one early-bird countdown'),
                (lambda soup: soup.main.append(deepcopy(soup.select_one('[data-early-bird-countdown]'))),
                 'expected one early-bird countdown'),
                (lambda soup: soup.select_one('[data-early-bird-countdown]').attrs.update(
                    {'data-deadline': '2026-12-30T23:00:00+01:00'}), 'countdown deadline disagrees'),
                (lambda soup: soup.select_one('[data-countdown-status] time').attrs.update(
                    datetime='2026-12-31'), 'status date disagrees'),
                (lambda soup: soup.select_one('[data-countdown-status] time').decompose(),
                 'status date disagrees'),
            ]:
                with self.subTest(page=page, detail=detail):
                    soup = BeautifulSoup(original, 'html.parser')
                    change(soup)
                    target.write_text(str(soup))
                    with self.assertRaisesRegex(GenerationError, detail):
                        self.check()
            target.write_text(original)

    def test_llm_output_uses_confirmed_edition_and_labels_retained_checkout(self):
        with patch.object(llms, 'ROOT_DIR', str(self.root)), \
             patch.object(llms, 'OUTPUT_FULL', str(self.root / 'llms-full.txt')), \
             patch.object(llms, 'OUTPUT_SUMMARY', str(self.root / 'llms.txt')), redirect_stdout(io.StringIO()):
            llms.main()
            before = {p.name: p.read_bytes() for p in self.root.glob('llms*.txt')}
            llms.main()
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.glob('llms*.txt')})
        summary = before['llms.txt'].decode()
        self.assertTrue(summary.startswith('# Milano Sensual Congress 2027\n'))
        for text in ('November 19-21, 2027', 'Devero Hotel', '2026 reference facts',
                     '2026 ticket reference only', 'This is not a 2027 checkout.',
                     'https://example.com/test-tickets', 'data/editions/2027.json'):
            self.assertIn(text, summary)
        self.assertNotIn('**Tickets are purchased externally**', summary)
        full = before['llms-full.txt'].decode()
        self.assertTrue(full.startswith('# Milano Sensual Congress 2027 - Full Site Documentation'))
        self.assertIn('not confirmed 2027 arrangements', full)


if __name__ == '__main__':
    unittest.main()
