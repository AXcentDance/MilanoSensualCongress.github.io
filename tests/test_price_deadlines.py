"""An expired sale must fail even if every copied price still agrees."""
from datetime import datetime
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import mock_open, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_price
from update_price import check_deadline, check_next_tier, check_social_pass, visit


class PriceDeadlineTests(unittest.TestCase):
    def check_ticket_html(self, checker, html):
        with patch('builtins.open', mock_open(read_data=html)):
            return checker('tickets.html')

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

    def test_unannounced_next_price_rejects_stale_cards_and_schema_references(self):
        with patch.object(update_price, 'NEXT_FULL_PASS_PRICE', None), \
                patch.object(update_price, 'NEXT_FULL_PASS_VALID_FROM', None):
            self.assertEqual(self.check_ticket_html(check_next_tier, '<main></main>'), [])
            for html in [
                '<div id="next-full-pass-tier">€135</div>',
                '<script type="application/ld+json">' + json.dumps({
                    'mentions': {'@id': update_price.NEXT_FULL_PASS_ID}}) + '</script>',
            ]:
                self.assertTrue(self.check_ticket_html(check_next_tier, html))

    def test_announced_next_price_still_requires_matching_card_and_offer(self):
        start = '2030-10-16T00:00:00+02:00'
        offer = {'@type': 'Offer', '@id': update_price.NEXT_FULL_PASS_ID,
                 'price': '140.00', 'priceCurrency': 'EUR',
                 'validFrom': start, 'availabilityStarts': start}
        html = '<script type="application/ld+json">' + json.dumps(offer) + '</script>' \
               '<div id="next-full-pass-tier"><span data-next-full-pass-price="140.00">€140</span>' \
               f'<time datetime="{start}">October 16</time></div>'
        with patch.object(update_price, 'NEXT_FULL_PASS_PRICE', '140.00'), \
                patch.object(update_price, 'NEXT_FULL_PASS_VALID_FROM', start):
            self.assertEqual(self.check_ticket_html(check_next_tier, html), [])
            self.assertTrue(self.check_ticket_html(check_next_tier, html.replace('€140', '€135')))
            self.assertTrue(self.check_ticket_html(check_next_tier, '<main></main>'))

    def test_partial_next_price_announcement_fails(self):
        with patch.object(update_price, 'NEXT_FULL_PASS_PRICE', '140.00'), \
                patch.object(update_price, 'NEXT_FULL_PASS_VALID_FROM', None):
            self.assertTrue(self.check_ticket_html(check_next_tier, '<main></main>'))

    def test_social_pass_requires_matching_price_availability_and_purchase_link(self):
        offer = {'@type': 'Offer', '@id': update_price.FULL_SOCIAL_PASS_ID,
                 'price': '75.00', 'priceCurrency': 'EUR',
                 'availability': 'https://schema.org/InStock', 'url': 'https://example.test/tickets'}
        html = '<script type="application/ld+json">' + json.dumps(offer) + '</script>' \
               '<div id="full-social-pass"><span data-full-social-pass-price="75.00">€75</span>' \
               '<a href="https://example.test/tickets">Buy Full Social Pass</a></div>'
        self.assertEqual(self.check_ticket_html(check_social_pass, html), [])
        for changed in [html.replace('€75', '€70'), html.replace('InStock', 'PreOrder'),
                        html.replace('"price": "75.00"', '"price": "70.00"'),
                        html.replace('href="https://example.test/tickets"', 'href="https://example.test/wrong"')]:
            self.assertTrue(self.check_ticket_html(check_social_pass, changed))


if __name__ == '__main__':
    unittest.main()
