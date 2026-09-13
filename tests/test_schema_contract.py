"""Regressions for valid JSON-LD that previously passed with wrong semantics."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_schema import check_dates, check_id_integrity
from schema_contract import SITE, check_graph


class SchemaContractTests(unittest.TestCase):
    def setUp(self):
        self.url = SITE + '/guide'
        self.page = {'@type': 'WebPage', '@id': self.url + '#webpage', 'url': self.url,
                     'inLanguage': 'en', 'isPartOf': {'@id': SITE + '/#website'},
                     'breadcrumb': {'@id': self.url + '#breadcrumb'}}
        self.breadcrumb = {'@type': 'BreadcrumbList', '@id': self.url + '#breadcrumb',
                           'itemListElement': [
                               {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
                               {'@type': 'ListItem', 'position': 2, 'name': 'Guide', 'item': self.url}]}
        self.data = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'Organization', '@id': SITE + '/#organization'},
            {'@type': 'WebSite', '@id': SITE + '/#website'}, self.page, self.breadcrumb]}
        self.body = '<nav aria-label="Breadcrumb" hidden><a href="/">Home</a><span>Guide</span></nav>'

    def check(self):
        soup = BeautifulSoup(f'<html lang="en"><head><link rel="canonical" href="{self.url}"></head>'
                             f'<body>{self.body}</body></html>', 'html.parser')
        return check_graph('guide.html', soup, self.data)

    def assert_issue(self, message):
        self.assertTrue(any(message in error for error in self.check()), self.check())

    def test_complete_subpage_graph_and_trail_pass(self):
        self.assertEqual(self.check(), [])

    def test_context_missing_page_id_and_dangling_local_entity_fail(self):
        self.data['@context'] = 'https://wrong.example'
        self.assert_issue('context')
        self.data['@context'] = 'https://schema.org'
        self.page.pop('@id')
        self.assert_issue('canonical #webpage')
        self.page['@id'] = self.url + '#webpage'
        self.page['mainEntity'] = {'@id': self.url + '#nonexistent'}
        self.assert_issue('unresolved local entity')

    def test_breadcrumb_positions_labels_and_destinations_are_checked(self):
        original = deepcopy(self.breadcrumb['itemListElement'])
        for key, value, diagnostic in [('position', 4, 'consecutive'), ('name', 'Wrong', 'labels'),
                                       ('item', SITE + '/another', 'final breadcrumb')]:
            with self.subTest(key=key):
                self.breadcrumb['itemListElement'] = deepcopy(original)
                self.breadcrumb['itemListElement'][-1][key] = value
                self.assert_issue(diagnostic)
        self.breadcrumb['itemListElement'] = original
        self.body = self.body.replace('href="/"', 'href="/news"')
        self.assert_issue('links disagree')

    def test_one_item_breadcrumb_is_not_accepted_as_a_google_trail(self):
        self.breadcrumb['itemListElement'].pop()
        self.assert_issue('at least two items')

    def test_missing_or_hidden_faq_content_fails_but_expandable_answers_pass(self):
        faq = {'@type': 'FAQPage', '@id': self.url + '#faq', 'mainEntity': [
            {'@type': 'Question', 'name': 'Is there a class?',
             'acceptedAnswer': {'@type': 'Answer', 'text': 'Yes, in <strong>English</strong>.'}}]}
        self.data['@graph'].append(faq)
        self.assert_issue('question is missing')
        self.body += '<details><summary>Is there a class?</summary><p>Yes, in English.</p></details>'
        self.assertEqual(self.check(), [])
        self.body = self.body.replace('<p>', '<p hidden>')
        self.assert_issue('answer is missing')

    def test_article_is_primary_and_contact_is_a_page_type(self):
        article = {'@type': 'BlogPosting', '@id': self.url + '#article', 'headline': 'Guide',
                   'author': {'@id': SITE + '/#organization'}, 'publisher': {'@id': SITE + '/#organization'},
                   'image': SITE + '/image.webp', 'datePublished': '2030-01-01', 'inLanguage': 'en',
                   'mainEntityOfPage': {'@id': self.url + '#webpage'}}
        self.data['@graph'].append(article)
        self.page['mainEntity'] = {'@id': SITE + '/#event'}
        self.assert_issue('article as primary')
        self.page['mainEntity'] = {'@id': article['@id']}
        self.assertEqual(self.check(), [])
        self.data['@graph'].append({'@type': 'ContactPage', 'mainEntityOfPage': {'@id': self.url + '#webpage'}})
        self.assert_issue('not a second page entity')

    def test_conditional_addons_preserve_currency_without_an_aggregate_range(self):
        admission = {'@type': 'Offer', 'price': '130.00', 'priceCurrency': 'EUR', 'addOn': [
            {'@type': 'Offer', 'price': '20.00', 'priceCurrency': 'CHF'}]}
        self.data['@graph'].append(admission)
        self.assertEqual(self.check(), [])
        aggregate = {'@type': 'AggregateOffer', 'lowPrice': '20.00', 'highPrice': '130.00',
                     'priceCurrency': 'EUR', 'offers': [admission, admission['addOn'][0]]}
        self.data['@graph'].append(aggregate)
        self.assert_issue('cannot mix currencies')
        aggregate['offers'] = [{'@type': 'Offer', 'price': '130.00', 'priceCurrency': 'EUR'}]
        self.assert_issue('price range disagrees')

    def test_course_needs_its_own_primary_entity_prerequisites_and_occurrence(self):
        self.data['@graph'].append({'@type': 'Course', '@id': self.url + '#course', 'name': 'Masterclass'})
        self.assert_issue('Course must be the primary')
        self.assert_issue('Course needs coursePrerequisites')
        self.data['@graph'].append({'@type': 'CourseInstance', 'location': {'@type': 'Place', 'name': 'Venue'}})
        self.assert_issue('venue address')
        self.assert_issue('CourseInstance needs inLanguage')

    def test_language_and_international_phone_format_are_checked(self):
        self.page['inLanguage'] = 'it'
        self.assert_issue('match HTML language')
        self.data['@graph'].append({'@type': 'ContactPoint', 'telephone': '079 123 45 67'})
        self.assert_issue('international country code')

    def test_couple_is_a_group_and_course_instructors_are_individuals(self):
        group = {'@type': 'PerformingGroup', '@id': SITE + '/artists#duo', 'name': 'Ana y Luis',
                 'member': [{'@type': 'Person', '@id': SITE + '/artists#ana', 'name': 'Ana'},
                            {'@type': 'Person', '@id': SITE + '/artists#luis', 'name': 'Luis'}]}
        instance = {'@type': 'CourseInstance', 'startDate': '2030-11-20', 'endDate': '2030-11-22',
                    'inLanguage': 'en', 'location': {'address': 'Venue'}, 'offers': {'price': '59.00'},
                    'superEvent': {'@id': SITE + '/#event'}, 'instructor': [{'@id': SITE + '/artists#ana'}]}
        self.data['@graph'].extend([group, instance])
        self.assertEqual(self.check(), [])
        instance['instructor'] = [{'@id': group['@id']}]
        self.assert_issue('individual Person')
        group['@type'] = 'Person'
        self.assert_issue('couple cannot be a single Person')

    def test_masterclass_offer_must_be_an_addon_of_admission(self):
        upgrade = {'@type': 'Offer', '@id': SITE + '/tickets#masterclass-upgrade', 'price': '59.00'}
        event = {'@type': 'DanceEvent', '@id': SITE + '/#event', 'offers': {'@type': 'Offer', 'price': '130.00'}}
        instance = {'@type': 'CourseInstance', '@id': SITE + '/masterclass#instance',
                    'startDate': '2030-11-20', 'endDate': '2030-11-22', 'inLanguage': 'en',
                    'location': {'address': 'Venue'}, 'instructor': [{'@type': 'Person', 'name': 'Ana'}],
                    'superEvent': {'@id': SITE + '/#event'}, 'offers': {'@id': upgrade['@id']}}
        self.data['@graph'].extend([event, upgrade, instance])
        self.assert_issue('Offer.addOn')
        event['offers']['addOn'] = [{'@id': upgrade['@id']}]
        self.assertEqual(self.check(), [])

    def test_impossible_timestamps_and_reversed_dates_fail(self):
        for node in [
            {'@type': 'DanceEvent', 'startDate': '2030-02-30T18:00:00+01:00'},
            {'@type': 'BlogPosting', 'dateModified': '2030-13-01'},
            {'@type': 'CourseInstance', 'startDate': '2030-11-22', 'endDate': '2030-11-20'},
            {'@type': 'DanceEvent', 'startDate': '2030-11-22T20:00:00Z', 'endDate': '2030-11-22T19:00:00Z'},
            {'@type': 'Offer', 'validFrom': '2030-09-16T00:00:00+02:00', 'validThrough': '2030-09-15T23:59:59+02:00'},
            {'@type': 'Offer', 'availabilityStarts': '2030-02-30T00:00:00+02:00'},
        ]:
            with self.subTest(node=node):
                errors = []
                check_dates('guide.html', node, errors, [])
                self.assertTrue(errors)

    def test_existing_page_does_not_validate_an_undefined_fragment(self):
        from unittest.mock import patch
        errors = []
        with patch('audit_schema.target_file_exists', return_value=True):
            check_id_integrity('guide.html', set(), {SITE + '/artists#missing'}, set(), errors, [])
        self.assertTrue(any('undefined entity' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
