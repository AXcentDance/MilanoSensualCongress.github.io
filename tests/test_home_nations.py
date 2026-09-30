"""Country statistics distinguish unknown data from zero and keep a fixed atlas."""
from copy import deepcopy
from decimal import Decimal
import json
import math
from pathlib import Path
import re
import sys
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_home_nations as nations


class HomeNationsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/community-2026.json').read_text())

    def selected(self):
        return next(country for country in self.data['countries'] if country['code'] == 'ES')

    def rendered(self, language='en'):
        return BeautifulSoup(nations.render(self.data, language), 'html.parser')

    def test_demo_roster_totals_are_consistent(self):
        self.assertEqual(self.data['statisticsMode'], 'demo')
        stats = [country['statistics'] for country in self.data['countries']]
        self.assertEqual(sum(Decimal(str(value['dancerPercent'])) for value in stats), Decimal('100'))
        self.assertTrue(all(isinstance(value['guestArtists'], int) and value['guestArtists'] >= 0 for value in stats))
        self.assertEqual(sum(value['guestArtists'] for value in stats), 100)
        italy = next(country for country in self.data['countries'] if country['code'] == 'IT')
        self.assertEqual(italy['statistics'], {'dancerPercent': 31, 'guestArtists': 31})

    def test_statistics_precede_the_complete_persistent_flag_picker(self):
        for language in ('en', 'it'):
            with self.subTest(language=language):
                soup = self.rendered(language)
                panel = soup.select_one('.nations-panel')
                blocks = panel.find_all('div', recursive=False)
                self.assertEqual([block['class'] for block in blocks],
                                 [['nations-passport'], ['nations-directory']])
                self.assertIsNone(panel.select_one('.nations-back'))
                directory = panel.select_one('.nations-directory')
                self.assertNotIn('hidden', directory.attrs)
                self.assertNotIn('inert', directory.attrs)
                self.assertEqual(len(directory.select('[data-country]')), len(self.data['countries']))
                self.assertEqual(panel.select_one('.nations-selected-name').get_text(strip=True),
                                 self.selected()['name'][language])

    def test_mobile_map_keeps_all_countries_with_real_origins_and_no_duplicate_desktop_hooks(self):
        for language in ('en', 'it'):
            with self.subTest(language=language):
                soup = self.rendered(language)
                mobile = soup.select_one('.nations-mobile')
                self.assertIsNotNone(mobile.select_one('.nations-pocket-heading p'))
                self.assertIsNone(mobile.select_one('h2'))
                pins = mobile.select('[data-mobile-country]')
                self.assertEqual(len(pins), len(self.data['countries']))
                self.assertEqual(len(soup.select('[data-country]')), len(self.data['countries']))
                self.assertEqual({pin['data-mobile-country'] for pin in pins if not pin.has_attr('hidden')},
                                 set(nations.POCKET_LABELS))
                self.assertTrue(all(pin.has_attr('disabled') for pin in pins))
                self.assertEqual([pin['data-mobile-country'] for pin in pins if pin['aria-pressed'] == 'true'], ['IT'])
                select = mobile.select_one('.nations-pocket-select')
                self.assertEqual(len(select.select('option')), len(self.data['countries']))
                self.assertEqual(select.select_one('option[selected]')['value'], 'IT')
                self.assertEqual(mobile.select_one('label')['for'], select['id'])
                self.assertEqual(len(mobile.select('noscript .nations-pocket-table tbody tr')), len(self.data['countries']))
                for country in self.data['countries']:
                    leader = mobile.select_one(f'[data-mobile-leader="{country["code"]}"] line')
                    origin, _ = nations.route_origin(country)
                    self.assertAlmostEqual(float(leader['x2']), origin[0] - nations.POCKET_CROP[0])
                    self.assertAlmostEqual(float(leader['y2']), origin[1] - nations.POCKET_CROP[1])

    def test_mobile_statistics_localize_and_only_label_demo_figures_as_preview(self):
        italy = next(country for country in self.data['countries'] if country['code'] == 'IT')
        for language, decimal in [('en', '12.5%'), ('it', '12,5%')]:
            for value, expected in [(0, '0%'), (12.5, decimal), (None, nations.COPY[language]['pending'])]:
                with self.subTest(language=language, value=value):
                    italy['statistics']['dancerPercent'] = value
                    mobile = self.rendered(language).select_one('.nations-mobile')
                    pin = mobile.select_one('[data-mobile-country="IT"]')
                    self.assertEqual(pin.select_one('strong').get_text(), '—' if value is None else expected)
                    self.assertIn(expected, pin['aria-label'])
                    self.assertIn(expected, mobile.select_one('.nations-pocket-status').get_text())
                    self.assertIn(nations.COPY[language]['pocketDemo'], mobile.select_one('.nations-pocket-note').get_text())
                    self.assertIn('{country}', mobile['data-mobile-status-template'])
                    self.assertIn('{percent}', mobile['data-mobile-outside-template'])
        self.data['statisticsMode'] = 'confirmed'
        for language in ('en', 'it'):
            self.assertEqual(self.rendered(language).select_one('.nations-pocket-note').get_text(),
                             nations.COPY[language]['pocketShare'])

    def test_zero_and_decimal_statistics_are_localized_without_losing_zero(self):
        for language, decimal in [('en', '12.5%'), ('it', '12,5%')]:
            for percentage, artists, expected in [(0, 0, '0%'), (12.5, 2, decimal)]:
                with self.subTest(language=language, percentage=percentage):
                    self.selected()['statistics'] = {'dancerPercent': percentage, 'guestArtists': artists}
                    soup = self.rendered(language)
                    self.assertEqual(soup.select_one('[data-nations-stat="dancers"]').get_text(strip=True), expected)
                    self.assertEqual(soup.select_one('[data-nations-stat="artists"]').get_text(strip=True), str(artists))
                    button = soup.select_one('[data-country="ES"]')
                    self.assertEqual(float(button['data-dancer-percent']), percentage)
                    self.assertEqual(int(button['data-guest-artists']), artists)
                    self.assertEqual(soup.select_one('.nations-stats')['aria-live'], 'polite')

    def test_unknown_statistics_are_pending_in_both_languages(self):
        for language, pending in [('en', 'To be confirmed'), ('it', 'Da confermare')]:
            with self.subTest(language=language):
                self.selected()['statistics'] = {'dancerPercent': None, 'guestArtists': None}
                soup = self.rendered(language)
                values = [value.get_text(strip=True) for value in soup.select('[data-nations-stat]')]
                self.assertEqual(values, [pending, pending])
                button = soup.select_one('[data-country="ES"]')
                self.assertEqual(button['data-dancer-percent'], '')
                self.assertEqual(button['data-guest-artists'], '')

    def test_invalid_statistics_cannot_be_published(self):
        original = deepcopy(self.selected())
        for key, invalid in [('dancerPercent', -0.1), ('dancerPercent', 100.1),
                             ('dancerPercent', math.inf), ('dancerPercent', math.nan),
                             ('dancerPercent', '12.5'), ('dancerPercent', True),
                             ('guestArtists', -1), ('guestArtists', 1.5),
                             ('guestArtists', '2'), ('guestArtists', True)]:
            with self.subTest(key=key, invalid=invalid):
                selected = self.selected()
                selected.clear()
                selected.update(deepcopy(original))
                selected['statistics'] = {'dancerPercent': None, 'guestArtists': None, key: invalid}
                with self.assertRaises(ValueError):
                    self.rendered()

    def test_confirmed_statistics_remain_available_without_javascript(self):
        for country in self.data['countries']:
            country['statistics'] = {'dancerPercent': None, 'guestArtists': None}
        self.selected()['statistics'] = {'dancerPercent': 0, 'guestArtists': 2}
        for language in ('en', 'it'):
            with self.subTest(language=language):
                soup = self.rendered(language)
                table = soup.select_one('noscript .nations-statistics-table')
                self.assertIsNotNone(table)
                self.assertEqual(len(table.select('tbody tr')), 1)
                cells = [cell.get_text(strip=True) for cell in table.select('tbody tr > *')]
                self.assertEqual(cells, [self.selected()['name'][language], '0%', '2'])

    def test_on_map_points_preserve_their_precise_origin(self):
        for point in [(100, 100), nations.MILANO, (24, 24), (776, 596)]:
            with self.subTest(point=point):
                origin, approximate = nations.route_origin({'mapPoint': list(point)})
                self.assertEqual(tuple(origin), point)
                self.assertFalse(approximate)

    def test_off_map_points_enter_from_the_correct_edge(self):
        for point, edge in [((-500, 362.42), (0, 24)), ((1800, 362.42), (0, 776)),
                            ((319.76, -500), (1, 24)), ((319.76, 1600), (1, 596))]:
            with self.subTest(point=point):
                origin, approximate = nations.route_origin({'mapPoint': list(point)})
                self.assertTrue(approximate)
                self.assertAlmostEqual(origin[edge[0]], edge[1])
                self.assert_curve_inside_map(origin)
        origin, approximate = nations.route_origin({'mapPoint': [100, 300], 'offMap': True})
        self.assertTrue(approximate)
        self.assertTrue(origin[0] in (24, 776) or origin[1] in (24, 596))
        self.assert_curve_inside_map(origin)

    def test_compass_directions_need_no_coordinates_or_larger_map(self):
        for direction in ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'):
            with self.subTest(direction=direction):
                origin, approximate = nations.route_origin({'mapDirection': direction})
                self.assertTrue(approximate)
                self.assertTrue(origin[0] in (24, 776) or origin[1] in (24, 596))
                if 'N' in direction:
                    self.assertLess(origin[1], nations.MILANO[1])
                if 'S' in direction:
                    self.assertGreater(origin[1], nations.MILANO[1])
                if 'W' in direction:
                    self.assertLess(origin[0], nations.MILANO[0])
                if 'E' in direction:
                    self.assertGreater(origin[0], nations.MILANO[0])
                self.assert_curve_inside_map(origin)

    def assert_curve_inside_map(self, origin):
        coordinates = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', nations.curve(origin))]
        self.assertEqual(coordinates[-2:], list(nations.MILANO))
        for x, y in zip(coordinates[::2], coordinates[1::2]):
            self.assertGreaterEqual(x, 24)
            self.assertLessEqual(x, 776)
            self.assertGreaterEqual(y, 24)
            self.assertLessEqual(y, 596)


if __name__ == '__main__':
    unittest.main()
