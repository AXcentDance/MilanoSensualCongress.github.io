"""Social metadata parity compares decoded values without hiding real mismatches."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import audit_og


class SocialMetadataTests(unittest.TestCase):
    def check(self, head, *, locale='en_US', allow_divergence=False, body=''):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / 'example.html'
            page.write_text(f'<html><head>{head}</head><body>{body}</body></html>', encoding='utf-8')
            with patch.object(audit_og, 'ROOT_DIR', directory), \
                 patch.object(audit_og, 'OG_TITLE_DIVERGENCE_ALLOWLIST',
                              {'example.html'} if allow_divergence else set()):
                return audit_og.check_file(page, locale)

    def metadata(self, *, title='Jack &amp; Jill', og_title='Jack &amp; Jill',
                 description='Artists & dancers', og_description='Artists &amp; dancers', locale='en_US'):
        return (f'<title>{title}</title><meta name="description" content="{description}">'
                f'<meta property="og:title" content="{og_title}">'
                f'<meta property="og:description" content="{og_description}">'
                f'<meta property="og:locale" content="{locale}">')

    def test_literal_named_and_numeric_entities_have_equal_values(self):
        for title, description in [('Jack & Jill', 'Artists & dancers'),
                                   ('Jack &amp; Jill', 'Artists &#38; dancers'),
                                   ('Jack &#x26; Jill', 'Artists &amp; dancers')]:
            with self.subTest(title=title, description=description):
                self.assertEqual(self.check(self.metadata(og_title=title, og_description=description)), [])

    def test_quotes_attribute_order_and_italian_entities_are_parsed(self):
        head = '''<title>L'artista &amp; la città</title>
            <META content="L'artista &amp; la città" NAME='description'>
            <meta content='L&#39;artista &#38; la città' PROPERTY='og:title'>
            <meta content='L&#39;artista &amp; la città' property='og:description'>
            <meta content='it_IT' property='og:locale'>'''
        self.assertEqual(self.check(head, locale='it_IT'), [])

    def test_a_real_description_mismatch_still_fails(self):
        errors = self.check(self.metadata(og_description='Artists &amp; teachers'))
        self.assertEqual(len(errors), 1)
        self.assertIn('Description vs OG Description mismatch', errors[0])

    def test_a_real_title_mismatch_still_fails(self):
        errors = self.check(self.metadata(og_title='Unrelated event'))
        self.assertEqual(len(errors), 1)
        self.assertIn('Title vs OG Title mismatch', errors[0])

    def test_existing_shorter_social_title_policy_is_preserved(self):
        self.assertEqual(self.check(self.metadata(title='Jack &amp; Jill | Milano Sensual Congress')), [])

    def test_title_allowlist_does_not_waive_locale_or_description_checks(self):
        errors = self.check(self.metadata(og_title='Approved social headline',
                            og_description='Different description', locale='it_IT'), allow_divergence=True)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any('Invalid og:locale' in error for error in errors))
        self.assertTrue(any('Description vs OG Description mismatch' in error for error in errors))
        self.assertFalse(any('Title mismatch' in error for error in errors))

    def test_missing_and_empty_social_tags_still_fail(self):
        for head in ['<title>Congress</title>', self.metadata(og_title='', og_description='', locale='')]:
            with self.subTest(head=head):
                self.assertEqual(self.check(head), ['Missing og:locale', 'Missing og:title', 'Missing og:description'])

    def test_body_metadata_cannot_replace_missing_head_metadata(self):
        self.assertEqual(self.check('<title>Congress</title>', body=self.metadata()),
                         ['Missing og:locale', 'Missing og:title', 'Missing og:description'])


if __name__ == '__main__':
    unittest.main()
