"""An expired sale must fail even if every copied price still agrees."""
from datetime import datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_price import check_deadline, visit


class PriceDeadlineTests(unittest.TestCase):
    def test_deadline_is_inclusive_and_compares_actual_instants(self):
        deadline = '2030-09-15T23:59:59+02:00'
        self.assertEqual(check_deadline(deadline, datetime.fromisoformat('2030-09-15T21:59:59+00:00')), [])
        self.assertTrue(check_deadline(deadline, datetime.fromisoformat('2030-09-15T22:00:00+00:00')))

    def test_invalid_or_ambiguous_deadlines_fail(self):
        for deadline in ['2030-02-30T23:59:59+01:00', '2030-09-15', '2030-09-15T23:59:59', 'TBA']:
            with self.subTest(deadline=deadline):
                self.assertTrue(check_deadline(deadline))

    def test_price_update_does_not_promote_next_tier_or_change_upgrade(self):
        current = {'@type': 'Offer', 'name': 'Current Full Pass', 'price': '130.00',
                   'validThrough': '2030-09-15T23:59:59+02:00', 'addOn': [
                       {'@type': 'Offer', 'name': 'Masterclass Upgrade', 'price': '59.00', 'priceCurrency': 'EUR'}]}
        upcoming = {'@type': 'Offer', 'name': 'Next Full Pass Tier', 'price': '135.00', 'priceCurrency': 'EUR'}
        visit([current, upcoming], '132.00', '2030-09-16T23:59:59+02:00', [], 'tickets.html', True)
        self.assertEqual(current['price'], '132.00')
        self.assertEqual(current['addOn'][0]['price'], '59.00')
        self.assertEqual(upcoming['price'], '135.00')


if __name__ == '__main__':
    unittest.main()
