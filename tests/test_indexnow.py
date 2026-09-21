"""Release-aware IndexNow selection and delivery; no real network submissions."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ping_indexnow as indexnow


class SelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'IndexNow tests')
        self.git('config', 'user.email', 'tests@example.invalid')
        for page in ['index.html', 'it/index.html', 'news/old.html', 'unchanged.html']:
            self.page(page)
        self.page('404.html', noindex=True)
        self.page('output/private.html')
        self.sitemap(['/', '/it/', '/news/old', '/unchanged'])
        self.before = self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def page(self, path, text='Congress', noindex=False):
        robots = '<meta name="robots" content="noindex">' if noindex else ''
        self.write(path, f'<html><head>{robots}</head><body>{text}</body></html>')

    def sitemap(self, paths):
        self.write('sitemap.xml', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                   + ''.join(f'<url><loc>{indexnow.DOMAIN}{path}</loc></url>' for path in paths)
                   + '</urlset>')

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'Fixture revision')
        return self.git('rev-parse', 'HEAD')

    def selected(self, **kwargs):
        return indexnow.changed_urls(self.before, self.root, **kwargs)

    def test_added_updated_renamed_and_removed_in_both_languages(self):
        self.page('index.html', 'Updated English')
        self.page('it/index.html', 'Italiano aggiornato')
        (self.root / 'news/old.html').rename(self.root / 'news/new.html')
        (self.root / 'unchanged.html').unlink()
        self.page('added.html')
        self.page('404.html', 'Changed utility', noindex=True)
        self.page('output/private.html', 'Changed private draft')
        self.sitemap(['/', '/it/', '/news/new', '/added'])
        self.commit()
        self.assertEqual(self.selected(), sorted(indexnow.DOMAIN + path for path in
                         ['/', '/it/', '/news/old', '/news/new', '/unchanged', '/added']))

    def test_no_content_change_does_not_notify(self):
        self.write('scripts/helper.py', '# Changed tooling')
        self.commit()
        self.assertEqual(self.selected(), [])

    def test_first_release_and_manual_recovery_include_all_public_pages(self):
        expected = sorted(indexnow.DOMAIN + path for path in ['/', '/it/', '/news/old', '/unchanged'])
        self.assertEqual(indexnow.changed_urls(None, self.root), expected)
        self.assertEqual(self.selected(all_pages=True), expected)

    def test_shared_content_revision_selects_unchanged_html(self):
        path = 'scripts/page_revisions.json'
        self.write(path, json.dumps({'pages': {'unchanged.html': {'fingerprint': 'old'}}}))
        self.before = self.commit()
        self.write(path, json.dumps({'pages': {'unchanged.html': {'fingerprint': 'new'}}}))
        self.commit()
        self.assertEqual(self.selected(), [indexnow.DOMAIN + '/unchanged'])

    def test_unknown_noindex_is_an_error(self):
        self.page('index.html', noindex=True)
        with self.assertRaisesRegex(RuntimeError, 'unexpected noindex'):
            self.selected()

    def test_previous_sitemap_cannot_introduce_foreign_urls(self):
        self.write('sitemap.xml', '<urlset><url><loc>https://example.com/</loc></url></urlset>')
        self.before = self.commit()
        with self.assertRaisesRegex(ValueError, 'Unexpected canonical URL'):
            self.selected()

    def test_invalid_baseline_is_not_silently_treated_as_no_changes(self):
        with self.assertRaises(subprocess.CalledProcessError):
            indexnow.changed_urls('nonexistent-revision', self.root)


def event():
    return {'repository': {'full_name': indexnow.REPOSITORY},
            'workflow_run': {'name': indexnow.PAGES_WORKFLOW, 'head_sha': 'current',
                             'head_branch': 'main', 'head_repository': {'full_name': indexnow.REPOSITORY},
                             'status': 'completed', 'conclusion': 'success'}}


class ReleaseTests(unittest.TestCase):
    def test_accepts_registered_workflow_name_as_well_as_run_display_name(self):
        payload = event()
        payload['workflow_run']['name'] = 'pages-build-deployment'
        builds = [{'status': 'built', 'commit': value} for value in ['current', 'previous']]
        with patch.object(indexnow, 'github_builds', return_value=builds):
            self.assertEqual(indexnow.release_range(payload, 'workflow_run', 'current'), ('previous', 'current'))

    def test_baseline_skips_failed_builds_and_repeated_current_builds(self):
        builds = [{'status': 'built', 'commit': 'current'},
                  {'status': 'built', 'commit': 'current'},
                  {'status': 'errored', 'commit': 'failed'},
                  {'status': 'built', 'commit': 'previous'}]
        with patch.object(indexnow, 'github_builds', return_value=builds):
            self.assertEqual(indexnow.release_range(event(), 'workflow_run', 'current'), ('previous', 'current'))

    def test_queued_and_failed_notifications_can_retry_after_newer_deployment(self):
        builds = [{'status': 'built', 'commit': value} for value in ['newer', 'current', 'previous']]
        with patch.object(indexnow, 'github_builds', return_value=builds):
            self.assertEqual(indexnow.release_range(event(), 'workflow_run', 'current'), ('previous', 'current'))

    def test_build_history_paginates(self):
        batches = [[{'status': 'built', 'commit': 'current'}] * 100,
                   [{'status': 'built', 'commit': 'previous'}]]
        with patch.object(indexnow, 'github_builds', side_effect=batches) as builds:
            self.assertEqual(indexnow.release_range(event(), 'workflow_run', 'current'), ('previous', 'current'))
            self.assertEqual([call.args[0] for call in builds.call_args_list], [1, 2])

    def test_first_publication_has_no_baseline(self):
        with patch.object(indexnow, 'github_builds', return_value=[{'status': 'built', 'commit': 'current'}]):
            self.assertEqual(indexnow.release_range(event(), 'workflow_run', 'current'), (None, 'current'))

    def test_untrusted_failed_or_mismatched_events_never_read_history(self):
        for field, value in [('conclusion', 'failure'), ('status', 'in_progress'),
                             ('head_branch', 'feature'), ('head_sha', 'unpublished'),
                             ('head_repository', {'full_name': 'elsewhere/fork'}), ('name', 'other')]:
            with self.subTest(field=field), patch.object(indexnow, 'github_builds') as builds:
                payload = event()
                payload['workflow_run'][field] = value
                with self.assertRaises(ValueError):
                    indexnow.release_range(payload, 'workflow_run', 'current')
                builds.assert_not_called()

    def test_manual_recovery_requires_published_main(self):
        payload = {'repository': {'full_name': indexnow.REPOSITORY}, 'ref': 'refs/heads/main'}
        with patch.object(indexnow, 'github_builds', return_value=[{'status': 'built', 'commit': 'previous'}]):
            with self.assertRaisesRegex(ValueError, 'finish publishing'):
                indexnow.release_range(payload, 'workflow_dispatch', 'current')

    def test_missing_successful_revision_is_a_failure(self):
        with patch.object(indexnow, 'github_builds', return_value=[{'status': 'built', 'commit': 'other'}]):
            with self.assertRaisesRegex(ValueError, 'absent'):
                indexnow.release_range(event(), 'workflow_run', 'current')


class DeliveryTests(unittest.TestCase):
    def response(self, status=200, body=b''):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.read.return_value = body
        return response

    def test_transient_errors_retry_then_accept_202(self):
        failure = HTTPError('https://api.indexnow.org', 429, 'Throttled', {}, None)
        with patch.object(indexnow, 'urlopen', side_effect=[failure, URLError('offline'), self.response(202)]), \
                patch.object(indexnow.time, 'sleep') as sleep:
            self.assertEqual(indexnow.request(Request('https://api.indexnow.org'), accepted=(200, 202)), (202, b''))
            self.assertEqual(sleep.call_count, 2)

    def test_permanent_and_exhausted_errors_fail(self):
        for code, attempts in [(403, 1), (503, 3)]:
            with self.subTest(code=code), patch.object(indexnow, 'urlopen', side_effect=
                    HTTPError('https://api.indexnow.org', code, 'error', {}, None)) as fetch, \
                    patch.object(indexnow.time, 'sleep'):
                with self.assertRaises(HTTPError):
                    indexnow.request(Request('https://api.indexnow.org'))
                self.assertEqual(fetch.call_count, attempts)

    def test_live_key_mismatch_prevents_submission(self):
        with patch.object(indexnow, 'request', return_value=(200, b'wrong')) as send:
            with self.assertRaisesRegex(ValueError, 'does not match'):
                indexnow.submit([indexnow.DOMAIN + '/'], 'existing-key')
            self.assertEqual(send.call_count, 1)

    def test_submission_batches_at_protocol_limit_and_uses_live_key(self):
        urls = [f'{indexnow.DOMAIN}/page-{n}' for n in range(10001)]
        with patch.object(indexnow, 'request', side_effect=[(200, b'existing-key'), (200, b''), (202, b'')]) as send, \
                redirect_stdout(io.StringIO()) as output:
            indexnow.submit(urls, 'existing-key')
        payloads = [json.loads(call.args[0].data) for call in send.call_args_list[1:]]
        self.assertEqual([len(p['urlList']) for p in payloads], [10000, 1])
        self.assertEqual(payloads[0]['keyLocation'], indexnow.DOMAIN + '/existing-key.txt')
        self.assertIn('key validation pending', output.getvalue())

    def test_dry_run_and_empty_selection_never_submit(self):
        for args, urls in [(['--before', 'HEAD', '--dry-run'], [indexnow.DOMAIN + '/']),
                           (['--before', 'HEAD'], [])]:
            with patch.object(indexnow, 'changed_urls', return_value=urls), \
                    patch.object(indexnow, 'urlopen', side_effect=AssertionError('Network forbidden')), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(indexnow.main(args), 0)

    def test_delivery_failure_propagates_to_workflow_exit(self):
        with patch.object(indexnow, 'changed_urls', return_value=[indexnow.DOMAIN + '/']), \
                patch.object(indexnow, 'verification_key', return_value='existing-key'), \
                patch.object(indexnow, 'submit', side_effect=URLError('unavailable')), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(indexnow.main(['--before', 'HEAD']), 1)

    def test_key_discovery_rejects_missing_or_ambiguous_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                indexnow.verification_key(root)
            (root / 'existing-key.txt').write_text('existing-key\n')
            self.assertEqual(indexnow.verification_key(root), 'existing-key')
            (root / 'second-key.txt').write_text('second-key')
            with self.assertRaises(ValueError):
                indexnow.verification_key(root)


if __name__ == '__main__':
    unittest.main()
