"""Package only public files for GitHub Pages; never upload the working tree."""
import argparse
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from bs4 import BeautifulSoup
from site_files import ROOT, site_pages

ASSET_DIRECTORIES = ('css', 'js', 'fonts', 'images', 'vendor', '.well-known')
PUBLIC_FILES = ('robots.txt', 'humans.txt', 'llms.txt', 'llms-full.txt',
                'sitemap.xml', 'feed.xml', 'it/feed.xml', 'CNAME', '.nojekyll')


def verify_references(destination):
    """Catch resources present in a checkout but missing from the release."""
    origin = 'https://milanosensualcongress.com'
    hostname = urlsplit(origin).netloc
    missing = []
    pending = sorted(destination.rglob('*.html'))
    visited = set()
    while pending:
        source = pending.pop()
        if source in visited:
            continue
        visited.add(source)
        content = source.read_text()
        references = re.findall(r'''url\(\s*["']?([^"')]+)''', content)
        if source.suffix == '.html':
            soup = BeautifulSoup(content, 'html.parser')
            for node in soup.find_all(True):
                references.extend(node.get(attribute) for attribute in
                                  ('href', 'src', 'poster', 'data-src') if node.get(attribute))
                srcset = node.get('srcset', '')
                if srcset and not srcset.lstrip().startswith('data:'):
                    references.extend(item.strip().split()[0] for item in srcset.split(',') if item.strip())
        relative = source.relative_to(destination).as_posix()
        for reference in references:
            if reference.strip().startswith(('#', '%23')):
                continue
            url = urlsplit(urljoin(origin + '/' + relative, reference.strip()))
            if url.scheme not in ('http', 'https') or url.netloc != hostname:
                continue
            target = destination / unquote(url.path).lstrip('/')
            candidates = (target, target / 'index.html', Path(str(target) + '.html'))
            found = next((path for path in candidates if path.is_file()
                          and path.resolve().is_relative_to(destination)), None)
            if found is None:
                missing.append(f'{relative}: {reference}')
            elif found.suffix == '.css':
                pending.append(found)
    if missing:
        raise ValueError('Missing packaged resources:\n' + '\n'.join(sorted(set(missing))))


def build_site(destination, root=ROOT):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('Use a fresh output directory; existing files are never removed.')
    files = set(site_pages(root))
    files.update(str(Path(page).with_suffix('.md')) for page in list(files)
                 if (root / Path(page).with_suffix('.md')).is_file())
    files.update(name for name in PUBLIC_FILES if (root / name).is_file())
    # IndexNow's public verification key is intentionally served at the root.
    files.update(path.name for path in root.glob('*.txt')
                 if len(path.stem) == 32 and all(c in '0123456789abcdef' for c in path.stem))
    for directory in ASSET_DIRECTORIES:
        files.update(path.relative_to(root).as_posix()
                     for path in (root / directory).rglob('*')
                     if path.is_file() and not any(part.startswith('.')
                         for part in path.relative_to(root / directory).parts))
    for name in sorted(files):
        source, target = root / name, destination / name
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError(f'Public file must be a regular local file: {name}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    verify_references(destination)
    return len(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.quality/site')
    args = parser.parse_args()
    print(f'Packaged {build_site(args.output)} public files in {args.output}')
