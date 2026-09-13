"""Prose review is actionable and read-only, never an automatic facts verdict."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bs4 import BeautifulSoup
from fact_copy_review import candidate_snippets, price_constants, review_copy
from generation_support import GenerationError
from congress_test_fixtures import write_homepages


class FactCopyReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_homepages(self.root)
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/update_price.py').write_text(
            'FULL_PASS_PRICE = "130.00"\nFULL_PASS_VALID_THROUGH = "2030-05-01T23:00:00Z"\n')
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.test')
        self.git('add', '.')
        self.git('commit', '-qm', 'Original facts')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def test_changed_dates_price_and_destination_list_copy_without_rewriting(self):
        price = self.root / 'scripts/update_price.py'
        price.write_text(price.read_text().replace('130.00', '140.00'))
        page = self.root / 'index.html'
        page.write_text(page.read_text().replace('2030-06-03T23:00:00+02:00', '2030-06-03T22:00:00+02:00')
                        .replace('https://example.com/test-tickets', 'https://example.com/new-tickets'))
        (self.root / 'tickets.html').write_text('<body><main><p>Full Pass €130 until May 1.</p>'
                                              '<p>Sunday social: 16:00–23:00</p></main></body>')
        originals = {path: path.read_bytes() for path in self.root.rglob('*')
                     if path.is_file() and '.git' not in path.parts}
        output = io.StringIO()
        with redirect_stdout(output):
            review_copy(self.root)
        text = output.getvalue()
        for value in ['endDate:', 'Full Pass price: 130.00 -> 140.00', 'ticket destination:',
                      'tickets.html:1', 'Full Pass €130', '16:00–23:00', 'not automatically errors',
                      'historical article facts']:
            self.assertIn(value, text)
        self.assertEqual(originals, {path: path.read_bytes() for path in originals})

    def test_equivalent_offsets_and_unchanged_sources_produce_no_changed_fact_report(self):
        page = self.root / 'index.html'
        page.write_text(page.read_text().replace('2030-06-01T18:00:00+02:00', '2030-06-01T16:00:00Z'))
        output = io.StringIO()
        with redirect_stdout(output):
            review_copy(self.root)
        self.assertIn('No shared source facts changed', output.getvalue())
        self.assertIn('does not validate arbitrary prose', output.getvalue())

    def test_missing_base_and_nonliteral_price_fail_explicitly(self):
        with self.assertRaisesRegex(GenerationError, 'Cannot compare'):
            review_copy(self.root, 'missing-commit')
        with self.assertRaisesRegex(GenerationError, 'Cannot read canonical price facts'):
            price_constants('FULL_PASS_PRICE = dangerous_call()')

    def test_adding_statistics_source_id_does_not_report_changed_statistics(self):
        originals = {path: (self.root / path).read_text() for path in ['index.html', 'it/index.html']}
        for path, text in originals.items():
            (self.root / path).write_text(text.replace(' id="congress-facts"', ''))
        self.git('add', '.')
        self.git('commit', '-qm', 'Same visible facts before source annotation')
        for path, text in originals.items():
            (self.root / path).write_text(text)
        output = io.StringIO()
        with redirect_stdout(output):
            review_copy(self.root)
        self.assertIn('No shared source facts changed', output.getvalue())

    def test_old_venue_and_ticket_destination_are_still_review_candidates(self):
        soup = BeautifulSoup('<body><main><p>Meet at Old Lodge.</p>'
                             '<a href="https://old.example">Book now</a></main></body>', 'html.parser')
        snippets = candidate_snippets(soup, {'offers', 'venue'},
                                      {'location.name': 'New Lodge', 'ticket destination': 'https://new.example'},
                                      {'location.name': 'Old Lodge', 'ticket destination': 'https://old.example'})
        self.assertEqual([snippet[2] for snippet in snippets], ['Meet at Old Lodge.', 'Book now'])

    def test_review_candidates_ignore_code_and_navigation_but_retain_historical_copy(self):
        soup = BeautifulSoup('<body><nav><a>€130</a></nav><script>€140</script><main>'
                             '<p>The May article records the previous Full Pass at €120.</p>'
                             '<div><span>€130</span></div><p>Test Venue, Test City</p></main></body>', 'html.parser')
        snippets = candidate_snippets(soup, {'offers', 'venue'}, {'location.name': 'Test Venue'})
        self.assertEqual([snippet[2] for snippet in snippets],
                         ['The May article records the previous Full Pass at €120.', '€130', 'Test Venue, Test City'])


if __name__ == '__main__':
    unittest.main()
