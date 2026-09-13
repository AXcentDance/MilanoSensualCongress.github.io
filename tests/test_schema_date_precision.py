"""Calendar-only lesson dates must not invent times or relax timed event checks."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_schema import check_dates


class SchemaDatePrecisionTests(unittest.TestCase):
    def check(self, node):
        issues, warnings = [], []
        check_dates('fixture.html', node, issues, warnings)
        return issues, warnings

    def test_valid_calendar_dates_on_course_instances_need_no_precision_warning(self):
        for types in ['CourseInstance', ['Event', 'CourseInstance']]:
            with self.subTest(types=types):
                self.assertEqual(self.check({'@type': types, 'startDate': '2026-11-20',
                                             'endDate': '2026-11-22'}), ([], []))
        self.assertEqual(self.check({'@type': 'CourseInstance', 'endDate': '2028-02-29'}), ([], []))

    def test_calendar_validation_rejects_impossible_course_dates(self):
        for field in ['startDate', 'endDate']:
            for value in ['2026-02-29', '2026-02-30', '2026-04-31', '2026-00-20', '2026-11-00']:
                with self.subTest(field=field, value=value):
                    issues, warnings = self.check({'@type': 'CourseInstance', field: value})
                    self.assertEqual(issues, [f'[fixture.html] malformed {field}: "{value}"'])
                    self.assertEqual(warnings, [])

    def test_dance_event_precision_remains_required_including_multiple_types(self):
        for types in ['DanceEvent', ['DanceEvent', 'CourseInstance']]:
            for field in ['startDate', 'endDate', 'validThrough']:
                with self.subTest(types=types, field=field):
                    issues, warnings = self.check({'@type': types, field: '2026-11-22'})
                    self.assertEqual(len(issues), 1)
                    self.assertIn('needs timezone offset', issues[0])
                    self.assertEqual(warnings, [])

    def test_timed_values_still_need_valid_timestamp_syntax_and_timezone(self):
        for types in ['CourseInstance', 'DanceEvent']:
            for field in ['startDate', 'endDate']:
                for value in ['2026-11-22T22:00:00', '2026-11-22 22:00:00+01:00', 'not a date']:
                    with self.subTest(types=types, field=field, value=value):
                        issues, warnings = self.check({'@type': types, field: value})
                        self.assertEqual(issues, [f'[fixture.html] malformed {field}: "{value}"'])
                        self.assertEqual(warnings, [])
                for value in ['2026-11-22T22:00:00+01:00', '2026-11-22T21:00:00Z']:
                    self.assertEqual(self.check({'@type': types, field: value}), ([], []))

    def test_other_date_only_warnings_are_preserved(self):
        for types, field in [('CourseInstance', 'datePublished'), ('CourseInstance', 'validThrough'),
                             ('Event', 'endDate'), ('DanceEvent', 'datePublished')]:
            with self.subTest(types=types, field=field):
                issues, warnings = self.check({'@type': types, field: '2026-11-22'})
                self.assertEqual(issues, [])
                self.assertEqual(len(warnings), 1)
                self.assertIn(f'date-only {field}', warnings[0])


if __name__ == '__main__':
    unittest.main()
