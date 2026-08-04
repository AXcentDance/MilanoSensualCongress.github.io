#!/usr/bin/env python3
"""Build a subset of Font Awesome containing only the icons used on the site.

Scans every HTML page for fa-* classes, maps them to codepoints via the full
all.min.css (kept in vendor/fontawesome/ as the pinned upstream reference),
subsets the woff2 fonts with fontTools, and writes a minimal stylesheet to
vendor/fontawesome/fa-subset.min.css.

Run from the repo root after adding any new Font Awesome icon:
    python3 scripts/build_fontawesome_subset.py

Requires: fonttools, brotli  (pip3 install --user fonttools brotli)
"""
import glob
import re
import subprocess
import sys

PAGES = (
    glob.glob('*.html')
    + glob.glob('it/*.html')
    + glob.glob('news/*.html')
    + glob.glob('it/news/*.html')
)

FAMILY_FONTS = {
    'solid': ('fa-solid-900', 'Font Awesome 6 Free', 900),
    'regular': ('fa-regular-400', 'Font Awesome 6 Free', 400),
    'brands': ('fa-brands-400', 'Font Awesome 6 Brands', 400),
}


def collect_icons():
    """Return {family: {icon-name}} for every fa-* class used in the pages."""
    icons_by_family = {'solid': set(), 'regular': set(), 'brands': set()}
    cls_re = re.compile(r'class="([^"]*\bfa-[^"]*)"')
    for path in PAGES:
        for m in cls_re.finditer(open(path).read()):
            classes = m.group(1).split()
            fam = 'solid'
            if 'fa-brands' in classes:
                fam = 'brands'
            elif 'fa-regular' in classes:
                fam = 'regular'
            for c in classes:
                if c.startswith('fa-') and c not in ('fa-solid', 'fa-regular', 'fa-brands'):
                    icons_by_family[fam].add(c[3:])
    return icons_by_family


def codepoint_map():
    """Map icon name -> hex codepoint from the pinned full FA stylesheet."""
    css = open('vendor/fontawesome/all.min.css').read()
    cp = {}
    for m in re.finditer(r'((?:\.fa-[a-z0-9-]+:before,?)+)\{content:"\\([0-9a-f]+)"\}', css):
        for name in re.findall(r'\.fa-([a-z0-9-]+):before', m.group(1)):
            cp[name] = m.group(2)
    return cp


def main():
    icons_by_family = collect_icons()
    cp = codepoint_map()

    missing = [(f, i) for f, icons in icons_by_family.items() for i in icons if i not in cp]
    if missing:
        print(f'WARNING: icons not found in all.min.css (skipped): {missing}')

    faces, all_used = [], {}
    for fam, icons in icons_by_family.items():
        icons = {i for i in icons if i in cp}
        if not icons:
            continue
        codes = sorted({cp[i] for i in icons})
        all_used.update({i: cp[i] for i in icons})
        fname, family, weight = FAMILY_FONTS[fam]
        subprocess.run(
            [
                sys.executable, '-m', 'fontTools.subset',
                f'vendor/fontawesome/webfonts/{fname}.ttf',
                '--unicodes=' + ','.join('U+' + c for c in codes),
                '--flavor=woff2',
                f'--output-file=vendor/fontawesome/webfonts/{fname}-subset.woff2',
            ],
            check=True,
        )
        faces.append(
            f'@font-face{{font-family:"{family}";font-style:normal;font-weight:{weight};'
            f'font-display:block;src:url(/vendor/fontawesome/webfonts/{fname}-subset.woff2) format("woff2")}}'
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
    open('vendor/fontawesome/fa-subset.min.css', 'w').write(out)
    print(f'OK: {len(all_used)} icons subset into vendor/fontawesome/fa-subset.min.css')


if __name__ == '__main__':
    main()
