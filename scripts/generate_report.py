#!/usr/bin/env python3
"""Save the maintained static quality gate's results as an honest Markdown report."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys

from generation_support import write_outputs

ROOT_DIR = Path(__file__).resolve().parent.parent


def generate_report(output=None, root=ROOT_DIR, *, overwrite=False):
    """Use the master command's exit status, preserving its diagnostics verbatim."""
    if output is None:
        output = Path(root) / '.quality' / 'reports' / (datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S-%fZ') + '.md')
    output = Path(output)
    if output.exists() and not overwrite:
        raise ValueError(f'{output} already exists; choose a new output or explicitly use --overwrite')
    command = [sys.executable, 'scripts/run_all_checks.py']
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        status = result.returncode
        stdout, stderr = result.stdout, result.stderr
    except OSError as error:
        status, stdout, stderr = 1, '', f'Unable to run static verification: {error}\n'

    outcome = 'PASS' if status == 0 else 'FAIL'
    lines = [
        '# Milano Sensual Congress — technical website report',
        '',
        f'**Result:** {outcome} (verification exit status {status})',
        f'**Generated:** {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
        '**Command:** `python3 scripts/run_all_checks.py`',
        '',
        'This report runs the same maintained static gate used by the delivery workflow.',
        'It includes its current checker coverage, cross-page metadata and sitemap checks,',
        'and all reported warnings and failures. A saved report can contain a failed audit.',
        '',
        'It does not run the separate regression suites, browser tests or Lighthouse,',
        'measure live search performance, or establish a ranking or overall SEO score.',
        '',
    ]
    for label, contents in [('Verification output', stdout), ('Standard error', stderr)]:
        if contents:
            # A longer fence preserves any fences printed in diagnostics.
            longest = max((len(part) for part in re.findall(r'`+', contents)), default=0)
            fence = '`' * max(3, longest + 1)
            lines.extend([f'## {label}', '', fence + 'text', contents.rstrip('\n'), fence, ''])

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_outputs({output: '\n'.join(lines) + '\n'})
    print(f'{outcome}: static verification; report saved to {output}')
    return 0 if status == 0 else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        help='report file (default: a new dated file under .quality/reports/)')
    parser.add_argument('--overwrite', action='store_true', help='explicitly replace an existing report')
    args = parser.parse_args(argv)
    try:
        return generate_report(args.output, overwrite=args.overwrite)
    except Exception as error:
        print(f'Report generation failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
