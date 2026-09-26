"""The approved-logo build publishes a complete set or preserves the prior set."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_official_logo as logo
import generation_support


class OfficialLogoTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.script = self.root / 'scripts/build_official_logo.py'
        self.script.parent.mkdir()
        shutil.copy2(ROOT / 'scripts/build_official_logo.py', self.script)
        source = self.root / logo.SOURCE.relative_to(ROOT)
        source.parent.mkdir(parents=True)
        source.write_bytes(b'approved source fixture')
        for name in logo.OUTPUTS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('previous ' + name).encode())

    def outputs(self):
        return {name: (self.root / name).read_bytes() for name in logo.OUTPUTS}

    def execute(self, convert):
        diagnostics = io.StringIO()
        with patch.object(subprocess, 'run', side_effect=convert), \
                redirect_stdout(diagnostics), redirect_stderr(diagnostics):
            try:
                runpy.run_path(str(self.script), run_name='__main__')
            except (subprocess.CalledProcessError, SystemExit, OSError) as error:
                return error, diagnostics.getvalue()
        return None, diagnostics.getvalue()

    def test_later_conversion_failure_preserves_every_previous_asset(self):
        before = self.outputs()
        calls = []

        def convert(command, **kwargs):
            calls.append(command)
            Path(command[-1]).write_bytes(b'partial or converted image')
            if len(calls) == 3:
                raise subprocess.CalledProcessError(1, command)

        error, _ = self.execute(convert)
        self.assertIsNotNone(error)
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.outputs(), before)

    def test_success_preserves_existing_assets_until_all_conversions_finish(self):
        before = self.outputs()
        expected = {name: ('converted ' + Path(name).name).encode() for name in logo.OUTPUTS}

        def convert(command, **kwargs):
            self.assertEqual(self.outputs(), before)
            destination = Path(command[-1])
            destination.write_bytes(('converted ' + destination.name).encode())

        error, _ = self.execute(convert)
        self.assertTrue(error is None or isinstance(error, SystemExit) and error.code == 0, error)
        self.assertEqual(self.outputs(), expected)

    def test_publication_failure_rolls_back_the_complete_set(self):
        before = self.outputs()
        replace = generation_support.os.replace
        calls = 0

        def fail_second_replace(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('simulated publication failure')
            return replace(source, destination)

        def convert(command, **kwargs):
            Path(command[-1]).write_bytes(b'converted image')

        with patch.object(generation_support.os, 'replace', side_effect=fail_second_replace):
            error, diagnostics = self.execute(convert)
        self.assertIsNotNone(error)
        self.assertIn('simulated publication failure', diagnostics)
        self.assertEqual(self.outputs(), before)


if __name__ == '__main__':
    unittest.main()
