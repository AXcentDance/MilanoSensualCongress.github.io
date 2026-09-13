"""Failures must reach callers without depending on human-readable success text."""
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import audit_links
import audit_assets
import generate_report
import run_all_checks

ROOT = Path(__file__).resolve().parents[1]


class CheckerProcessTests(unittest.TestCase):
    def run_checker(self, script, html):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'index.html').write_text(html, encoding='utf-8')
            return subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                                  cwd=directory, capture_output=True, text=True)

    def test_html_syntax_error_reaches_the_cli_exit_status(self):
        result = self.run_checker('check_html_syntax.py', '<html><body><div></body></html>')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Unclosed tag <div>', result.stdout)

    def test_valid_html_has_a_successful_exit(self):
        result = self.run_checker('check_html_syntax.py', '<html><body><h1>Congress</h1></body></html>')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_head_link_coverage_survives_retirement_of_report_only_checker(self):
        result = self.run_checker('audit_links.py', '<html><head><link rel="stylesheet" href="missing.css"></head></html>')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('missing.css', result.stdout)

    def test_page_read_failure_cannot_be_reported_as_a_successful_link_audit(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(audit_links, 'site_pages', return_value=['missing.html']), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(audit_links.audit_relative_links(directory), 1)
            self.assertIn('page could not be checked', output.getvalue())
            self.assertNotIn('SUCCESS:', output.getvalue())

    def test_link_audit_resolves_encoded_relative_filenames_and_query_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text('<a href="travel%20guide.html?lang=en#airport">Travel</a>')
            (root / 'travel guide.html').write_text('<h1 id="airport">Airport</h1>')
            with patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(audit_links.audit_relative_links(root), 0)

    def test_schema_checks_cannot_be_bypassed_by_script_attribute_formatting(self):
        for attrs in ["data-purpose='schema' type='application/ld+json'",
                      'TYPE="application/ld+json" id="schema"']:
            with self.subTest(attrs=attrs):
                result = self.run_checker('audit_schema.py',
                    '<html><head><script ' + attrs + '>{"@type":"DanceEvent",'
                    '"startDate":"2026-11-20"}</script></head><body></body></html>')
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('needs timezone offset', result.stdout)

    def test_unique_asset_coverage_is_active_in_the_master_gate(self):
        self.assertTrue(any(args == ['scripts/audit_assets.py']
                            for args, _label in run_all_checks.CHECKERS))
        with tempfile.TemporaryDirectory() as directory, \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            Path(directory, 'index.html').write_text('''<html><head>
                <style>.hero { background-image: url("images/missing.webp"); }</style>
                </head><body><video><source src="video/missing.mp4"></video>
                <script src="js/missing.js?v=2"></script></body></html>''')
            self.assertEqual(audit_assets.audit_assets(directory), 1)
            for missing in ['images/missing.webp', 'video/missing.mp4', 'js/missing.js?v=2']:
                self.assertIn(missing, output.getvalue())

    def test_asset_audit_uses_public_discovery_and_accepts_existing_resources(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('sys.stdout', new_callable=io.StringIO):
            root = Path(directory)
            (root / 'index.html').write_text('''<html><body style="background:url('/photo.webp?v=1')">
                <script src="site.js?v=2"></script><style>.filter{filter:url(#svg-filter)}</style>
                <img src="owned-by-image-checker.webp" alt=""></body></html>''')
            (root / 'site.js').write_text('')
            (root / 'photo.webp').write_bytes(b'fixture')
            (root / '.quality').mkdir()
            (root / '.quality/report.html').write_text('<script src="not-public.js"></script>')
            self.assertEqual(audit_assets.audit_assets(root), 0)

    def test_success_does_not_require_magic_words_and_warnings_remain_visible(self):
        result = subprocess.CompletedProcess([], 0, 'A new success message\nWARNING: review this\n', '')
        with patch.object(run_all_checks, 'CHECKERS', [(['example.py'], 'Example check')]), \
             patch.object(run_all_checks, 'FAILURES', []) as failures, \
             patch.object(run_all_checks.subprocess, 'run', return_value=result), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            run_all_checks.run_absorbed_checkers()
            self.assertEqual(failures, [])
            self.assertIn('WARNING: review this', output.getvalue())

    def test_a_checker_that_cannot_start_fails_and_other_checkers_still_run(self):
        with patch.object(run_all_checks, 'CHECKERS', [(['one.py'], 'One'), (['two.py'], 'Two')]), \
             patch.object(run_all_checks, 'FAILURES', []) as failures, \
             patch.object(run_all_checks.subprocess, 'run', side_effect=[
                 OSError('cannot execute'), subprocess.CompletedProcess([], 0, '', '')]) as execute, \
             patch('sys.stdout', new_callable=io.StringIO):
            run_all_checks.run_absorbed_checkers()
            self.assertEqual(execute.call_count, 2)
            self.assertEqual(len(failures), 1)
            self.assertIn('could not run', failures[0])


class ReportProcessTests(unittest.TestCase):
    def test_default_report_creates_dated_evidence_without_overwriting_prior_report(self):
        result = subprocess.CompletedProcess([], 0, 'PASS\n', '')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(generate_report.subprocess, 'run', return_value=result), \
             patch('sys.stdout', new_callable=io.StringIO):
            root = Path(directory)
            historical = root / 'System/audit_report.md'
            historical.parent.mkdir()
            historical.write_text('Original historical evidence')
            self.assertEqual(generate_report.generate_report(root=root), 0)
            before = {path: path.read_bytes() for path in (root / '.quality/reports').glob('*.md')}
            self.assertEqual(len(before), 1)
            self.assertEqual(generate_report.generate_report(root=root), 0)
            self.assertEqual(len(list((root / '.quality/reports').glob('*.md'))), 2)
            self.assertEqual(before, {path: path.read_bytes() for path in before})
            self.assertEqual(historical.read_text(), 'Original historical evidence')
            self.assertRegex(next(iter(before)).name, r'^\d{4}-\d{2}-\d{2}T.*Z\.md$')

    def test_existing_report_requires_explicit_overwrite_before_running_gate(self):
        result = subprocess.CompletedProcess([], 0, 'PASS\n', '')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(generate_report.subprocess, 'run', return_value=result) as execute, \
             patch('sys.stdout', new_callable=io.StringIO):
            target = Path(directory, 'report.md')
            target.write_text('Prior evidence')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                generate_report.generate_report(target)
            self.assertEqual(target.read_text(), 'Prior evidence')
            execute.assert_not_called()
            self.assertEqual(generate_report.generate_report(target, overwrite=True), 0)
            self.assertIn('**Result:** PASS', target.read_text())

    def test_report_uses_the_master_gate_and_preserves_failed_diagnostics(self):
        result = subprocess.CompletedProcess([], 3,
            'WARNING: date needs review\n```quoted diagnostic```\nFAILED: sitemap missing\n', 'parse failed\n')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(generate_report.subprocess, 'run', return_value=result) as execute, \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            target = Path(directory, 'report.md')
            self.assertEqual(generate_report.generate_report(target), 1)
            report = target.read_text()
            self.assertIn('**Result:** FAIL (verification exit status 3)', report)
            self.assertIn('WARNING: date needs review', report)
            self.assertIn('parse failed', report)
            self.assertIn('FAILED: sitemap missing', report)
            self.assertIn('````text', report)
            self.assertIn('FAIL: static verification', output.getvalue())
            self.assertEqual(execute.call_args.args[0], [sys.executable, 'scripts/run_all_checks.py'])
            self.assertEqual(execute.call_args.kwargs['cwd'], generate_report.ROOT_DIR)

    def test_successful_report_does_not_claim_browser_or_ranking_results(self):
        result = subprocess.CompletedProcess([], 0, 'PASS: static checks\n', '')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(generate_report.subprocess, 'run', return_value=result), \
             patch('sys.stdout', new_callable=io.StringIO):
            target = Path(directory, 'report.md')
            self.assertEqual(generate_report.generate_report(target), 0)
            report = target.read_text()
            self.assertIn('**Result:** PASS', report)
            self.assertIn('does not run the separate regression suites', report)
            self.assertIn('or establish a ranking or overall SEO score', report)

    def test_failure_to_start_verification_produces_a_failed_report(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(generate_report.subprocess, 'run', side_effect=OSError('cannot execute')), \
             patch('sys.stdout', new_callable=io.StringIO):
            target = Path(directory, 'report.md')
            self.assertEqual(generate_report.generate_report(target), 1)
            self.assertIn('Unable to run static verification', target.read_text())

    def test_report_write_failure_is_not_a_success(self):
        result = subprocess.CompletedProcess([], 0, 'PASS\n', '')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(generate_report.subprocess, 'run', return_value=result), \
             patch.object(generate_report, 'write_outputs', side_effect=OSError('disk full')), \
             patch('sys.stderr', new_callable=io.StringIO) as output:
            self.assertEqual(generate_report.main(['--output', str(Path(directory, 'report.md'))]), 1)
            self.assertIn('Report generation failed: disk full', output.getvalue())


if __name__ == '__main__':
    unittest.main()
