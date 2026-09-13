"""Shared facts must stay consistent without copying production constants."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_event_facts
import event_facts
import generate_llms_text as llms
from generation_support import GenerationError
from congress_test_fixtures import facts, write_homepages


class EventFactsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_homepages(self.root)

    def test_llm_outputs_follow_source_facts_and_are_repeatable(self):
        with patch.object(llms, 'ROOT_DIR', str(self.root)), \
             patch.object(llms, 'OUTPUT_FULL', str(self.root / 'llms-full.txt')), \
             patch.object(llms, 'OUTPUT_SUMMARY', str(self.root / 'llms.txt')), redirect_stdout(io.StringIO()):
            llms.main()
            before = {p.name: p.read_bytes() for p in self.root.glob('llms*.txt')}
            llms.main()
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.glob('llms*.txt')})
        summary = before['llms.txt'].decode()
        for value in ['Test Congress 2030', 'June 1-3, 2030', 'Test Venue', '2,000+ dancers',
                      '2.000+ ballerini', 'https://example.com/test-tickets']:
            self.assertIn(value, summary)
        self.assertNotIn('2026', summary)
        self.assertNotIn('Generated automatically on', before['llms-full.txt'].decode())

    def test_missing_source_and_conflicting_translations_fail(self):
        page = self.root / 'it/index.html'
        text = page.read_text()
        page.write_text(text.replace('2.000+', '3.000+'))
        with self.assertRaisesRegex(GenerationError, 'statistics quantities disagree'):
            event_facts.load_current_facts(self.root)
        page.write_text(text.replace('2030-06-03T23:00', '2030-06-03T22:00'))
        with self.assertRaisesRegex(GenerationError, 'endDate disagrees'):
            event_facts.load_current_facts(self.root)
        page.write_text(text.replace('id="congress-facts"', 'id="unrelated"'))
        with self.assertRaisesRegex(GenerationError, '#congress-facts'):
            event_facts.load_current_facts(self.root)

    def test_same_entity_conflicts_fail_but_subevents_and_translations_remain_valid(self):
        event = deepcopy(facts()['event'])
        event['description'] = 'Una descrizione italiana'
        event['location']['description'] = 'Descrizione del luogo'
        subevent = deepcopy(event)
        subevent['@id'] += '-party'
        subevent['endDate'] = '2030-06-02T22:00:00+02:00'
        target = self.root / 'program.html'
        def write():
            target.write_text('<head><script type="application/ld+json">' +
                              json.dumps({'@graph': [event, subevent]}) + '</script></head><main>Program</main>')
        write()
        with redirect_stdout(io.StringIO()):
            check_event_facts.check(self.root)
        event['endDate'] = '2030-06-03T22:00:00+02:00'
        write()
        with self.assertRaisesRegex(GenerationError, 'program.html: congress endDate'):
            check_event_facts.check(self.root)

    def test_invalid_dates_or_malformed_graphs_fail(self):
        for value in ['2030-06-01', '2030-06-01T18:00:00', '2030-02-30T18:00:00Z', 'not a date']:
            event = facts()['event']
            event['startDate'] = value
            with self.subTest(value=value), self.assertRaisesRegex(GenerationError, 'invalid congress dates'):
                event_facts.core_event(event, 'index.html')
        page = self.root / 'index.html'
        page.write_text(page.read_text().replace('"@graph":', '"@graph" BROKEN:'))
        with self.assertRaisesRegex(GenerationError, 'index.html: invalid JSON-LD'):
            event_facts.load_current_facts(self.root)

    def test_utc_and_equivalent_offsets_compare_as_instants_without_rewriting_sources(self):
        page = self.root / 'it/index.html'
        text = page.read_text().replace('2030-06-01T18:00:00+02:00', '2030-06-01T16:00:00Z')
        text = text.replace('2030-06-03T23:00:00+02:00', '2030-06-03T21:00:00+00:00')
        page.write_text(text)
        target = self.root / 'program.html'
        target.write_text(text)
        sources = {path: path.read_bytes() for path in [self.root / 'index.html', page, target]}
        with redirect_stdout(io.StringIO()):
            check_event_facts.check(self.root)
        self.assertEqual(sources, {path: path.read_bytes() for path in sources})
        loaded = event_facts.load_current_facts(self.root)
        self.assertEqual(loaded['event']['startDate'], '2030-06-01T18:00:00+02:00')

    def test_summary_dates_use_rome_calendar_in_summer_and_winter(self):
        for start, end, expected in [
            ('2030-05-31T22:30:00Z', '2030-06-03T21:00:00Z', 'June 1-3, 2030'),
            ('2026-11-20T23:30:00Z', '2026-11-22T21:00:00Z', 'November 21-22, 2026'),
        ]:
            event = facts()['event']
            event.update(startDate=start, endDate=end)
            self.assertEqual(event_facts.date_range(event), expected)

    def test_event_date_order_uses_instants(self):
        event = facts()['event']
        event.update(startDate='2030-06-01T10:00:00+02:00', endDate='2030-06-01T07:30:00Z')
        with self.assertRaisesRegex(GenerationError, 'end must follow start'):
            event_facts.core_event(event, 'index.html')

    def test_aggregate_ticket_destination_and_non_bare_definitions_cannot_bypass_check(self):
        target = self.root / 'tickets.html'
        event = deepcopy(facts()['event'])
        def write():
            target.write_text('<head><script type="application/ld+json">' +
                              json.dumps({'@graph': [event, {'@id': event_facts.EVENT_ID}]}) +
                              '</script></head><main>Tickets</main>')
        event['offers'] = {'@type': 'AggregateOffer', 'url': 'https://wrong.example/tickets'}
        write()
        with self.assertRaisesRegex(GenerationError, 'ticket URL disagrees'):
            check_event_facts.check(self.root)
        event['offers'] = facts()['event']['offers']
        for bad_type in [None, 'Organization']:
            if bad_type:
                event['@type'] = bad_type
            else:
                event.pop('@type', None)
            write()
            with self.assertRaisesRegex(GenerationError, 'must have type DanceEvent'):
                check_event_facts.check(self.root)
        event['@type'] = ['Event', 'DanceEvent']
        write()
        with redirect_stdout(io.StringIO()):
            check_event_facts.check(self.root)

    def test_optional_organization_details_and_root_slash_are_valid_but_wrong_name_fails(self):
        target = self.root / 'booking.html'
        organization = {'@id': event_facts.ORGANIZATION_ID, '@type': 'Organization',
                        'name': 'Test Organization', 'url': 'https://example.com/'}
        def write():
            target.write_text('<head><script type="application/ld+json">' +
                              json.dumps(organization) + '</script></head><main>Booking</main>')
        write()
        with redirect_stdout(io.StringIO()):
            check_event_facts.check(self.root)
        organization['name'] = 'Wrong organization'
        write()
        with self.assertRaisesRegex(GenerationError, 'organization name disagrees'):
            check_event_facts.check(self.root)


if __name__ == '__main__':
    unittest.main()
