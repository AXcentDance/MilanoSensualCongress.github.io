"""A failed prerequisite must stop dependent public-output generation."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from subprocess import CompletedProcess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sync_indexes


class SyncWorkflowTests(unittest.TestCase):
    def test_stops_after_failed_step_and_reports_partial_work(self):
        results = [CompletedProcess([], 0), CompletedProcess([], 3)]
        stderr = io.StringIO()
        with patch.object(sync_indexes.subprocess, 'run', side_effect=results) as run, \
             redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            self.assertEqual(sync_indexes.main(), 1)
        self.assertEqual(run.call_count, 2)
        self.assertIn('Earlier steps may have updated files', stderr.getvalue())
        self.assertIn('exit 3', stderr.getvalue())

    def test_missing_interpreter_is_a_failure_not_success(self):
        with patch.object(sync_indexes.subprocess, 'run', side_effect=OSError('cannot execute')) as run, \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(sync_indexes.main(), 1)
        self.assertEqual(run.call_count, 1)
        self.assertIn('cannot execute', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
