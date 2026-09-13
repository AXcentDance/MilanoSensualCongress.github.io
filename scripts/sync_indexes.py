#!/usr/bin/env python3
"""Run the maintained derived-content workflow in order, stopping on failure."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STEPS = (
    'check_event_facts.py',
    'sync_social_meta.py',
    'generate_md_twins.py',
    'generate_rss.py',
    'generate_sitemap.py',
    'generate_llms_text.py',
)


def main():
    for script in STEPS:
        print(f'Running {script}...', flush=True)
        try:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script)], cwd=ROOT)
        except OSError as error:
            print(f'Index synchronization stopped at {script}: {error}', file=sys.stderr)
            return 1
        if result.returncode:
            print(f'Index synchronization stopped at {script} (exit {result.returncode}). '
                  'Earlier steps may have updated files; fix the error and rerun the workflow.', file=sys.stderr)
            return 1
    print('Index synchronization complete. Review the diff and run npm run check.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
