"""Shared parser, error reporting, and staged writes for site generators."""
import os
from pathlib import Path
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


def scan_error(error):
    raise GenerationError(f'Cannot scan input directory: {error}') from error


def verify_outputs(outputs):
    """Compare the generator's own rendering without changing any files."""
    stale = []
    for path, data in outputs.items():
        expected = data.encode('utf-8') if isinstance(data, str) else data
        try:
            actual = Path(path).read_bytes()
        except OSError:
            actual = None
        if actual != expected:
            stale.append(str(path))
    if stale:
        raise GenerationError('Generated files are missing or stale: ' + ', '.join(stale)
                              + '. Run npm run sync:indexes, then repeat verification.')


def write_outputs(outputs, *, remove=()):
    """Stage a complete set, then replace files; roll back handled write failures.

    Replacements are atomic per file, not a crash-atomic multi-file transaction.
    Retain recovery copies and report their location if rollback itself fails.
    """
    outputs = {Path(path).absolute(): data for path, data in outputs.items()}
    removals = {Path(path).absolute() for path in remove}
    if removals & outputs.keys():
        raise GenerationError('An output cannot also be scheduled for removal')
    for target, data in outputs.items():
        if not isinstance(data, (str, bytes)) or not data or (isinstance(data, str) and not data.strip()):
            raise GenerationError(f'{target}: generated output is empty or invalid')
    targets = list(outputs) + sorted(removals)
    staging = {}
    staged_outputs = {}
    replaced = []
    backups = {}
    preserve_recovery = False
    try:
        for target in targets:
            if target.parent not in staging:
                staging[target.parent] = Path(tempfile.mkdtemp(prefix='.generation-', dir=target.parent))
            directory = staging[target.parent]
            backup = directory / (target.name + '.old')
            if target.exists():
                shutil.copy2(target, backup)
                backups[target] = backup
            else:
                backups[target] = None
            if target in outputs:
                staged = directory / target.name
                data = outputs[target]
                if isinstance(data, bytes):
                    staged.write_bytes(data)
                else:
                    staged.write_text(data, encoding='utf-8')
                if backups[target] is not None:
                    shutil.copymode(backup, staged)
                staged_outputs[target] = staged
        for target in targets:
            if target in outputs:
                os.replace(staged_outputs[target], target)
            else:
                target.unlink(missing_ok=True)
            replaced.append(target)
    except (Exception, KeyboardInterrupt) as error:
        recovery_errors = []
        for target in reversed(replaced):
            try:
                if backups[target] is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(backups[target], target)
            except OSError as recovery_error:
                recovery_errors.append(f'{target}: {recovery_error}')
        if recovery_errors:
            preserve_recovery = True
            detail = f'Rollback failed for {"; ".join(recovery_errors)}. Recovery files: {", ".join(map(str, staging.values()))}'
        else:
            detail = 'Previous outputs are unchanged.'
        raise GenerationError(f'Cannot write generated outputs: {error}. {detail}') from error
    finally:
        if not preserve_recovery:
            for directory in staging.values():
                shutil.rmtree(directory, ignore_errors=True)


def run_generator(generate):
    try:
        generate()
    except Exception as error:
        print(f'Generation failed: {error}', file=sys.stderr)
        return 1
    return 0
