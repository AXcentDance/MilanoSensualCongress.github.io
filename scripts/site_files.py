"""Shared public-page discovery. Tool output must never enter site indexes."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = {'node_modules', 'vendor', 'scripts', 'tests', 'System', 'test-results',
            'playwright-report', '__pycache__'}


def ignored_directory(name):
    return name.startswith('.') or name in EXCLUDED


def site_pages(root=ROOT):
    root = Path(root)
    found = []
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not ignored_directory(d))
        found.extend(Path(directory, name).relative_to(root).as_posix()
                     for name in files if name.endswith('.html'))
    return sorted(found)


if __name__ == '__main__':
    import json
    print(json.dumps(site_pages()))
