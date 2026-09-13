#!/usr/bin/env python3
"""Check private-file exclusions and, before committing, release completeness.

This reads Git's index; it never stages, commits or publishes anything.
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ('.agent/context/', 'output/')


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f'git {args[0]} failed')
    return result.stdout


def inspect_release(root=ROOT, staged=False):
    tracked = git(root, 'ls-files', '-z').split('\0')
    failures = [f'Private file is in the Git index: {path}' for path in tracked
                if path.startswith(PRIVATE)]
    for prefix in PRIVATE:
        probe = prefix + 'publication-check.txt'
        ignored = subprocess.run(['git', 'check-ignore', '--no-index', '-q', probe], cwd=root)
        if ignored.returncode != 0:
            failures.append(f'Private directory lacks a Git exclusion: {prefix}')
    untracked = [path for path in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0') if path]
    if staged:
        failures.extend(f'Untracked file needs an explicit include/exclude decision: {path}' for path in untracked)
        unstaged = [path for path in git(root, 'diff', '--name-only', '-z', '--').split('\0') if path]
        for path in unstaged:
            # Existing Finder metadata is unrelated user work. Do not require
            # staging it merely to complete an otherwise selected release.
            if Path(path).name == '.DS_Store' and subprocess.run(
                    ['git', 'check-ignore', '--no-index', '-q', path], cwd=root).returncode == 0:
                continue
            failures.append(f'Incomplete selected release: tracked file has unstaged changes: {path}. '
                            'Review and include or resolve them before checking the staged release.')
    elif untracked:
        print(f'WARNING: {len(untracked)} nonignored files are not in Git yet. Before committing, review them and run python3 scripts/check_release_files.py --staged.')
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true', help='also reject nonignored files omitted from the Git index')
    args = parser.parse_args(argv)
    try:
        failures = inspect_release(staged=args.staged)
    except (OSError, RuntimeError) as error:
        failures = [str(error)]
    for failure in failures:
        print('FAIL: ' + failure)
    if not failures:
        print('PASS: private files excluded' + (' and release file selection complete' if args.staged else ''))
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
