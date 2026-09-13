"""Freshness checks and release selection must fail safely without writing."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_release_files
import generate_llms_text as llms
import generate_rss as rss
import run_all_checks
from generation_support import GenerationError
from congress_test_fixtures import write_homepages


class ExportFreshnessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_homepages(self.root)
        for page in ['news/article.html', 'it/news/articolo.html']:
            target = self.root / page
            target.parent.mkdir(parents=True, exist_ok=True)
            graph = {'@context': 'https://schema.org', '@graph': [
                {'@type': 'BlogPosting', 'datePublished': '2026-06-01T08:00:00Z'}]}
            target.write_text('<html><head><title>Congress news</title>'
                              '<meta name="description" content="Original description">'
                              '<script type="application/ld+json">' + json.dumps(graph) +
                              '</script></head><body><main><article>Original article</article></main></body></html>')
        for owner, name, value in [(rss, 'ROOT_DIR', str(self.root)), (llms, 'ROOT_DIR', str(self.root)),
                                   (llms, 'OUTPUT_FULL', str(self.root / 'llms-full.txt')),
                                   (llms, 'OUTPUT_SUMMARY', str(self.root / 'llms.txt'))]:
            setting = patch.object(owner, name, value)
            setting.start()
            self.addCleanup(setting.stop)
        with redirect_stdout(io.StringIO()):
            rss.main()
            llms.main()

    def snapshot(self):
        return {path.relative_to(self.root): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.root.rglob('*') if path.is_file()}

    def test_fresh_real_exports_pass_without_rewriting(self):
        before = self.snapshot()
        with redirect_stdout(io.StringIO()):
            rss.main(check=True)
            llms.main(check=True)
        self.assertEqual(before, self.snapshot())

    def test_each_feed_and_each_llm_export_is_checked_without_repairing_it(self):
        for name, generator in [('feed.xml', rss.main), ('it/feed.xml', rss.main),
                                ('llms.txt', llms.main), ('llms-full.txt', llms.main)]:
            with self.subTest(output=name):
                path = self.root / name
                fresh = path.read_bytes()
                path.write_bytes(b'stale but existing output')
                before = self.snapshot()
                with redirect_stdout(io.StringIO()), self.assertRaises(GenerationError) as caught:
                    generator(check=True)
                self.assertIn(str(path), str(caught.exception))
                self.assertEqual(before, self.snapshot())
                path.write_bytes(fresh)

    def test_changed_article_source_makes_feeds_and_llm_exports_stale(self):
        page = self.root / 'it/news/articolo.html'
        page.write_text(page.read_text().replace('Original description', 'Updated description'))
        before = self.snapshot()
        for generator in [rss.main, llms.main]:
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(GenerationError, 'missing or stale'):
                generator(check=True)
        self.assertEqual(before, self.snapshot())

    def test_missing_output_is_reported_without_creating_it(self):
        for name in ['feed.xml', 'it/feed.xml']:
            (self.root / name).unlink()
        before = self.snapshot()
        with redirect_stdout(io.StringIO()), self.assertRaises(GenerationError) as caught:
            rss.main(check=True)
        self.assertIn(str(self.root / 'feed.xml'), str(caught.exception))
        self.assertIn(str(self.root / 'it/feed.xml'), str(caught.exception))
        self.assertEqual(before, self.snapshot())

    def test_real_check_clis_return_failure_without_rewriting_stale_exports(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        for name in ['generate_rss.py', 'generate_llms_text.py', 'site_files.py', 'generation_support.py',
                     'article_metadata.py', 'event_facts.py', 'iso_dates.py']:
            shutil.copy2(ROOT / 'scripts' / name, scripts / name)
        (self.root / 'feed.xml').write_text('stale feed')
        (self.root / 'llms-full.txt').write_text('stale full export')
        before = {path: path.read_bytes() for path in [self.root / 'feed.xml', self.root / 'it/feed.xml',
                                                      self.root / 'llms.txt', self.root / 'llms-full.txt']}
        for name in ['generate_rss.py', 'generate_llms_text.py']:
            result = subprocess.run([sys.executable, str(scripts / name), '--check'], cwd=self.root,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('missing or stale', result.stderr)
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_master_gate_uses_read_only_export_checks(self):
        commands = {args[0]: args[1:] for args, _label in run_all_checks.CHECKERS}
        for name in ['generate_rss.py', 'generate_llms_text.py', 'generate_sitemap.py']:
            self.assertEqual(commands['scripts/' + name], ['--check'])


class ReleaseSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.test')
        (self.root / '.gitignore').write_text('.agent/context/\noutput/\n.DS_Store\n')
        (self.root / 'main.py').write_text('original = True\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Original release')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def test_new_required_helper_omission_is_rejected_without_staging(self):
        (self.root / 'main.py').write_text('import required_helper\n')
        (self.root / 'required_helper.py').write_text('ready = True\n')
        self.git('add', 'main.py')
        before = self.git('ls-files', '--stage')
        failures = check_release_files.inspect_release(self.root, staged=True)
        self.assertTrue(any('required_helper.py' in failure for failure in failures), failures)
        self.assertEqual(before, self.git('ls-files', '--stage'))
        self.git('add', 'required_helper.py')
        self.assertEqual(check_release_files.inspect_release(self.root, staged=True), [])

    def test_forced_private_index_additions_are_rejected_even_when_ignored(self):
        for name in ['.agent/context/private.md', 'output/private-draft.html']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('private fixture')
            self.git('add', '-f', name)
        failures = check_release_files.inspect_release(self.root, staged=True)
        self.assertEqual(sum('Private file is in the Git index:' in failure for failure in failures), 2)

    def test_worktree_only_gitignore_exclusions_cannot_certify_staged_release(self):
        target = self.root / '.gitignore'
        target.write_text('.DS_Store\n')
        self.git('add', '.gitignore')
        target.write_text('.agent/context/\noutput/\n.DS_Store\n')
        failures = check_release_files.inspect_release(self.root, staged=True)
        self.assertTrue(any('unstaged changes: .gitignore' in failure for failure in failures), failures)

    def test_tracked_unstaged_source_or_export_is_rejected(self):
        (self.root / 'main.py').write_text('changed = True\n')
        failures = check_release_files.inspect_release(self.root, staged=True)
        self.assertTrue(any('Incomplete selected release' in failure and 'main.py' in failure for failure in failures), failures)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(check_release_files.inspect_release(self.root), [])

    def test_ignored_finder_metadata_is_allowed_but_other_tracked_edits_are_not(self):
        path = self.root / '.DS_Store'
        path.write_bytes(b'original user metadata')
        self.git('add', '-f', '.DS_Store')
        path.write_bytes(b'changed user metadata')
        self.assertEqual(check_release_files.inspect_release(self.root, staged=True), [])
        self.assertEqual(path.read_bytes(), b'changed user metadata')


if __name__ == '__main__':
    unittest.main()
