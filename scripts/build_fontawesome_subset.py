#!/usr/bin/env python3
"""Build a subset of Font Awesome containing only the icons used on the site.

Scans HTML pages and shared JavaScript for fa-* classes, maps them to codepoints
via the full all.min.css (kept in vendor/fontawesome/ as the pinned reference),
subsets the woff2 fonts with fontTools, and writes a minimal stylesheet to
vendor/fontawesome/fa-subset.min.css.

Run from the repo root after adding any new Font Awesome icon:
    python3 scripts/build_fontawesome_subset.py

Requires: fonttools, brotli  (pip3 install --user fonttools brotli)
"""
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from generation_support import GenerationError, read_page, run_generator, write_outputs
from site_files import ROOT, site_pages

FAMILY_FONTS = {
    'solid': ('fa-solid-900', 'Font Awesome 6 Free', 900),
    'regular': ('fa-regular-400', 'Font Awesome 6 Free', 400),
    'brands': ('fa-brands-400', 'Font Awesome 6 Brands', 400),
}


def family_classes(classes):
    return {family for family in FAMILY_FONTS if 'fa-' + family in classes}


def collect_icons(root=ROOT):
    """Scan complete class attributes and resolve dynamic additions explicitly.

    For unresolved dynamic targets, declare the bounded icon set beside its JS:
        // fontawesome-dynamic: brands instagram whatsapp
    Never default an unresolved classList addition to the solid family.
    """
    root = Path(root)
    icons_by_family = {family: set() for family in FAMILY_FONTS}
    documents = [(page, read_page(root / page)) for page in site_pages(root)]
    pages = [soup for _, soup in documents]
    known = {}

    def add(classes, origin, families=None):
        names = {name[3:] for name in classes if name.startswith('fa-')
                 and name[3:] not in FAMILY_FONTS}
        if not names:
            return
        families = family_classes(classes) if families is None else families
        if not families:
            families = {'solid'}  # Complete HTML/className values use FA's base family.
        if len(families) != 1:
            raise GenerationError(f'{origin}: conflicting Font Awesome families {sorted(families)}')
        family = next(iter(families))
        icons_by_family[family].update(names)
        for name in names:
            known.setdefault(name, set()).add(family)

    for page, soup in documents:
        for tag in soup.find_all(class_=True):
            add(tag['class'], page)

    def selector_families(expression):
        match = re.fullmatch(r'document\.(querySelector|getElementById)\(\s*(["\'])(.*?)\2\s*\)', expression)
        if not match:
            return set()
        method, _, selector = match.groups()
        found = set()
        for soup in pages:
            nodes = soup.find_all(id=selector) if method == 'getElementById' else soup.select(selector)
            for node in nodes:
                found.update(family_classes(node.get('class', [])))
        return found

    scripts = [(f'{page}: inline script {index + 1}', script.get_text())
               for page, soup in documents
               for index, script in enumerate(soup.find_all('script'))
               if not script.get('src') and script.get('type', '').lower() not in {'application/ld+json', 'speculationrules'}]
    for path in sorted((root / 'js').rglob('*.js')):
        if any(part.startswith('.') for part in path.relative_to(root).parts):
            continue
        scripts.append((str(path.relative_to(root)), path.read_text(encoding='utf-8')))
    for path, source in scripts:
        declared = {}
        for family, names in re.findall(r'fontawesome-dynamic:\s*(solid|regular|brands)\s+([a-z0-9 -]+)', source):
            for name in names.split():
                name = name.removeprefix('fa-')
                declared.setdefault(name, set()).add(family)
                add(['fa-' + family, 'fa-' + name], path)
        if (re.search(r'''["']fa-["']\s*\+''', source) or 'fa-${' in source) and not declared:
            raise GenerationError(f'{path}: constructed icon names need a fontawesome-dynamic declaration')
        for group in re.findall(r'class(?:Name)?\s*=\s*["\'`]([^"\'`]+)', source):
            if '${' in group and 'fa-' in group:
                if not declared:
                    raise GenerationError(f'{path}: dynamic icon template needs a fontawesome-dynamic declaration')
                continue
            add(re.findall(r'\bfa(?:-[a-z0-9-]+)?\b', group), path)
        bindings = {}
        query = r'document\.(?:querySelector|getElementById)\([^)]*\)'
        for name, expression in re.findall(r'(?:const|let|var)\s+([\w$]+)\s*=\s*(' + query + ')', source):
            bindings.setdefault(name, set()).update(selector_families(expression))
        for name, _, classes in re.findall(r'([\w$]+)\.className\s*=\s*(["\'`])([^"\'`]+)', source):
            bindings.setdefault(name, set()).update(family_classes(classes.split()))
        pattern = r'(' + query + r'|[\w$]+)\.classList\.(?:add|toggle|replace)\(([^)]*)\)'
        for target, arguments in re.findall(pattern, source):
            classes = re.findall(r'\bfa(?:-[a-z0-9-]+)?\b', arguments)
            explicit = family_classes(classes)
            context = bindings.get(target, set()) or selector_families(target)
            for name in {value[3:] for value in classes if value.startswith('fa-') and value[3:] not in FAMILY_FONTS}:
                families = explicit or context or declared.get(name) or known.get(name, set())
                if len(families) != 1:
                    raise GenerationError(f'{path}: cannot determine family for dynamic fa-{name}; add an explicit family or fontawesome-dynamic declaration')
                if context and declared.get(name) and context != declared[name]:
                    raise GenerationError(f'{path}: declaration conflicts with target family for fa-{name}')
                add(['fa-' + name], path, families)
    return icons_by_family


def codepoint_map(root=ROOT):
    """Map icon name -> hex codepoint from the pinned full FA stylesheet."""
    css = (Path(root) / 'vendor/fontawesome/all.min.css').read_text(encoding='utf-8')
    cp = {}
    for m in re.finditer(r'((?:\.fa-[a-z0-9-]+:before,?)+)\{content:"\\([0-9a-f]+)"\}', css):
        for name in re.findall(r'\.fa-([a-z0-9-]+):before', m.group(1)):
            cp[name] = m.group(2)
    return cp


def validate_glyphs(font, codes):
    from fontTools.ttLib import TTFont
    try:
        with TTFont(font) as source:
            available = source.getBestCmap() or {}
        missing = [code for code in codes if int(code, 16) not in available]
        if missing:
            raise ValueError(f'codepoints {missing} do not exist in this font family; check fa-solid/fa-regular/fa-brands')
    except Exception as error:
        raise GenerationError(f'Cannot use {font}: {error}') from error


def main(root=ROOT):
    root = Path(root)
    missing_dependencies = [name for name in ('fontTools', 'brotli') if importlib.util.find_spec(name) is None]
    if missing_dependencies:
        raise GenerationError(f'Missing {", ".join(missing_dependencies)}. Install with: {sys.executable} -m pip install fonttools brotli')
    icons_by_family = collect_icons(root)
    cp = codepoint_map(root)

    missing = [(f, i) for f, icons in icons_by_family.items() for i in icons if i not in cp]
    if missing:
        raise GenerationError(f'Font Awesome icons not found in the pinned all.min.css: {sorted(missing)}. Correct the class names or explicitly support the required icons before rebuilding.')
    if not any(icons_by_family.values()):
        raise GenerationError('No Font Awesome icons found; refusing to replace the existing subset with an empty build')

    faces, all_used, outputs = [], {}, {}
    for fam, icons in icons_by_family.items():
        if not icons:
            continue
        codes = sorted({cp[i] for i in icons})
        all_used.update({i: cp[i] for i in icons})
        fname, family, weight = FAMILY_FONTS[fam]
        font = root / f'vendor/fontawesome/webfonts/{fname}.ttf'
        validate_glyphs(font, codes)
        with tempfile.TemporaryDirectory(prefix='msc-font-') as temporary:
            staged = Path(temporary) / f'{fname}-subset.woff2'
            command = [
                sys.executable, '-m', 'fontTools.subset',
                str(font),
                '--unicodes=' + ','.join('U+' + c for c in codes),
                '--flavor=woff2',
                f'--output-file={staged}',
            ]
            result = subprocess.run(command, text=True, capture_output=True)
            if result.returncode:
                raise GenerationError(f'Cannot build {fname}: {result.stderr.strip()}')
            if not staged.is_file() or staged.stat().st_size == 0:
                raise GenerationError(f'Cannot build {fname}: fontTools produced no font')
            font_bytes = staged.read_bytes()
            version = hashlib.sha256(font_bytes).hexdigest()[:16]
            filename = f'{fname}-subset.{version}.woff2'
            outputs[root / 'vendor/fontawesome/webfonts' / filename] = font_bytes
        faces.append(
            f'@font-face{{font-family:"{family}";font-style:normal;font-weight:{weight};'
            f'font-display:block;src:url(/vendor/fontawesome/webfonts/{filename}) format("woff2")}}'
        )

    rules = ''.join(
        f'.fa-{name}:before{{content:"\\{code}"}}' for name, code in sorted(all_used.items())
    )
    base = (
        '.fa,.fa-brands,.fa-regular,.fa-solid{-moz-osx-font-smoothing:grayscale;'
        '-webkit-font-smoothing:antialiased;display:var(--fa-display,inline-block);'
        'font-style:normal;font-variant:normal;line-height:1;text-rendering:auto}'
        '.fa,.fa-solid{font-family:"Font Awesome 6 Free";font-weight:900}'
        '.fa-regular{font-family:"Font Awesome 6 Free";font-weight:400}'
        '.fa-brands{font-family:"Font Awesome 6 Brands";font-weight:400}'
    )
    out = (
        '/* Font Awesome 6.4.0 subset - only icons used on this site. '
        'Regenerate with scripts/build_fontawesome_subset.py */\n'
        + ''.join(faces) + base + rules
    )
    outputs[root / 'vendor/fontawesome/fa-subset.min.css'] = out
    write_outputs(outputs)
    print(f'OK: {len(all_used)} icons subset into vendor/fontawesome/fa-subset.min.css')


if __name__ == '__main__':
    raise SystemExit(run_generator(main))
