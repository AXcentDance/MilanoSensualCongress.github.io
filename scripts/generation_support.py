"""Shared parser, error reporting, and staged writes for public index generators."""
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import tempfile

try:
    from bs4 import BeautifulSoup
except ImportError as error:
    requirements = Path(__file__).resolve().parents[1] / 'requirements-dev.txt'
    command = f'{shlex.quote(sys.executable)} -m pip install -r {shlex.quote(str(requirements))}'
    raise SystemExit(f'Beautiful Soup is required for complete generation ({error}).\nInstall the declared dependencies:\n{command}') from None


class GenerationError(RuntimeError):
    pass


def read_page(filepath):
    try:
        content = Path(filepath).read_text(encoding='utf-8')
        if not content.strip():
            raise ValueError('HTML file is empty')
        return BeautifulSoup(content, 'html.parser')
    except Exception as error:
        raise GenerationError(f'Cannot read or parse {filepath}: {error}') from error


def is_noindexed(soup):
    return any('noindex' in meta.get('content', '').lower()
               for meta in soup.find_all('meta', attrs={'name': re.compile('^robots$', re.I)}))


def scan_error(error):
    raise GenerationError(f'Cannot scan input directory: {error}') from error


def write_outputs(outputs):
    """Stage a complete set, then replace files; roll back handled write failures.

    Replacements are atomic per file, not a crash-atomic multi-file transaction.
    Retain recovery copies and report their location if rollback itself fails.
    """
    outputs = {Path(path).absolute(): text for path, text in outputs.items()}
    for target, text in outputs.items():
        if not isinstance(text, str) or not text.strip():
            raise GenerationError(f'{target}: generated output is empty or invalid')
    parents = {path.parent for path in outputs}
    if len(parents) != 1:
        raise GenerationError('Generated outputs must share one directory')
    staging = None
    replaced = []
    backups = {}
    preserve_recovery = False
    try:
        staging = Path(tempfile.mkdtemp(prefix='.generation-', dir=parents.pop()))
        for target, text in outputs.items():
            backup = staging / (target.name + '.old')
            if target.exists():
                shutil.copy2(target, backup)
                backups[target] = backup
            else:
                backups[target] = None
            staged = staging / target.name
            staged.write_text(text, encoding='utf-8')
            if backups[target] is not None:
                shutil.copymode(backup, staged)
        for target in outputs:
            os.replace(staging / target.name, target)
            replaced.append(target)
    except (Exception, KeyboardInterrupt) as error:
        recovery_errors = []
        for target in reversed(replaced):
            try:
                if backups[target] is None:
                    target.unlink()
                else:
                    os.replace(backups[target], target)
            except OSError as recovery_error:
                recovery_errors.append(f'{target}: {recovery_error}')
        if recovery_errors:
            preserve_recovery = True
            detail = f'Rollback failed for {"; ".join(recovery_errors)}. Recovery files: {staging}'
        else:
            detail = 'Previous outputs are unchanged.'
        raise GenerationError(f'Cannot write generated outputs: {error}. {detail}') from error
    finally:
        if staging is not None and not preserve_recovery:
            shutil.rmtree(staging, ignore_errors=True)


def run_generator(generate):
    try:
        generate()
    except Exception as error:
        print(f'Generation failed: {error}', file=sys.stderr)
        return 1
    return 0
