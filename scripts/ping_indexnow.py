"""Notify IndexNow after a successful Pages release; --dry-run never submits."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from site_files import indexable_pages, page_url_path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = 'https://milanosensualcongress.com'
REPOSITORY = 'AXcentDance/MilanoSensualCongress.github.io'
PAGES_WORKFLOW = 'pages build and deployment'
RETRYABLE = {429, 500, 502, 503, 504}


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def request(request, accepted=(200,)):
    """Bound retries; permanent errors must fail the notification job."""
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                if response.status not in accepted:
                    raise RuntimeError(f'Unexpected HTTP {response.status} from {request.full_url}')
                return response.status, response.read()
        except HTTPError as error:
            if error.code not in RETRYABLE or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def github_builds(page):
    token = os.environ.get('GH_TOKEN')
    if not token:
        raise ValueError('GH_TOKEN is required to verify the published Pages build')
    _, body = request(Request(
        f'https://api.github.com/repos/{REPOSITORY}/pages/builds?per_page=100&page={page}',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'msc-indexnow'}))
    return json.loads(body)


def release_range(event, event_name, head):
    """Use successful publication history, including changes after failed builds.

    A queued/retried notification may describe an older successful publication:
    search engines still fetch the latest live content at its changed URLs.
    Manual recovery targets the currently published main commit only.
    """
    if event.get('repository', {}).get('full_name') != REPOSITORY:
        raise ValueError('Unexpected repository in release event')
    if event_name == 'workflow_run':
        run = event.get('workflow_run', {})
        if (run.get('name') != PAGES_WORKFLOW or run.get('head_branch') != 'main'
                or run.get('head_repository', {}).get('full_name') != REPOSITORY
                or run.get('status') != 'completed' or run.get('conclusion') != 'success'):
            raise ValueError('IndexNow requires a successful main Pages deployment')
        if run.get('head_sha') != head:
            raise ValueError('Checkout does not match the completed Pages deployment')
    elif event_name != 'workflow_dispatch' or event.get('ref') != 'refs/heads/main':
        raise ValueError('Unsupported release event or branch')

    page = 1
    found = False
    while True:
        builds = github_builds(page)
        if page == 1:
            if not builds:
                raise ValueError('No Pages build history is available')
            if event_name == 'workflow_dispatch' and (
                    builds[0]['status'] != 'built' or builds[0]['commit'] != head):
                raise ValueError('Wait for main to finish publishing before retrying IndexNow')
        for build in builds:
            if build['status'] != 'built':
                continue
            if build['commit'] == head:
                found = True
            elif found:
                return build['commit'], head
        if len(builds) < 100:
            if not found:
                raise ValueError('Completed revision is absent from successful Pages build history')
            return None, head  # First publication: notify all indexable pages.
        page += 1


def old_urls(before, root):
    """The published sitemap preserves canonical URLs for removed/renamed pages."""
    tree = ET.fromstring(git(root, 'show', f'{before}:sitemap.xml'))
    urls = {node.text for node in tree.findall('{*}url/{*}loc')}
    if not urls:
        raise ValueError('Previous sitemap has no URLs')
    for url in urls:
        parts = urlsplit(url or '')
        if (parts.scheme != 'https' or parts.netloc != urlsplit(DOMAIN).netloc
                or not parts.path.startswith('/') or parts.query or parts.fragment):
            raise ValueError(f'Unexpected canonical URL in previous sitemap: {url}')
    return urls


def changed_urls(before, root=ROOT, all_pages=False):
    current = {DOMAIN + page_url_path(page) for page in indexable_pages(root)}
    if not current:
        raise ValueError('No indexable public pages found')
    if not before or set(before) == {'0'}:
        return sorted(current)
    before = git(root, 'rev-parse', '--verify', '--end-of-options', f'{before}^{{commit}}')
    previous = old_urls(before, root)
    # Disable rename detection so both the old URL and the replacement are sent.
    changed = git(root, 'diff', '--no-renames', '--name-only', '-z', before, 'HEAD', '--', '*.html')
    candidates = {DOMAIN + page_url_path(path) for path in changed.split('\0') if path}
    selected = (candidates & (current | previous)) | (current ^ previous)
    # Shared content/media changes can affect a page without changing its HTML.
    revision_path = 'scripts/page_revisions.json'
    revision_file = Path(root) / revision_path
    if revision_file.exists() and git(root, 'ls-tree', '--name-only', before, '--', revision_path):
        old = json.loads(git(root, 'show', f'{before}:{revision_path}'))['pages']
        new = json.loads(revision_file.read_text())['pages']
        selected.update(DOMAIN + page_url_path(page) for page, value in new.items()
                        if value.get('fingerprint') != old.get(page, {}).get('fingerprint')
                        and DOMAIN + page_url_path(page) in current)
    return sorted(selected | current if all_pages else selected)


def verification_key(root=ROOT):
    """Reuse the existing public ownership file; no extra repository secret."""
    matches = [path.stem for path in Path(root).glob('*.txt')
               if re.fullmatch(r'[A-Za-z0-9-]{8,128}', path.stem)
               and path.read_text(encoding='utf-8').strip() == path.stem]
    if len(matches) != 1:
        raise ValueError('Expected exactly one IndexNow verification file at the site root')
    return matches[0]


def submit(urls, key):
    key_url = f'{DOMAIN}/{key}.txt'
    _, body = request(Request(key_url, headers={'User-Agent': 'msc-indexnow'}))
    if body.decode('utf-8').strip() != key:
        raise ValueError('Live IndexNow verification file does not match the release')
    for offset in range(0, len(urls), 10000):
        batch = urls[offset:offset + 10000]
        payload = {'host': urlsplit(DOMAIN).netloc, 'key': key,
                   'keyLocation': key_url, 'urlList': batch}
        status, _ = request(Request('https://api.indexnow.org/indexnow',
                                   data=json.dumps(payload).encode('utf-8'),
                                   headers={'Content-Type': 'application/json; charset=utf-8',
                                            'User-Agent': 'msc-indexnow'}), accepted=(200, 202))
        pending = ' (key validation pending)' if status == 202 else ''
        print(f'IndexNow HTTP {status}: {len(batch)} URLs received{pending}. Indexing is not guaranteed.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--before', help='previous published Git revision')
    source.add_argument('--github-event', action='store_true', help='verify release using GitHub Pages history')
    parser.add_argument('--all', action='store_true', help='also resend every current indexable page')
    parser.add_argument('--dry-run', action='store_true', help='print URLs without verifying the key or submitting')
    args = parser.parse_args(argv)
    try:
        before = args.before
        if args.github_event:
            event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
            release = release_range(event, os.environ['GITHUB_EVENT_NAME'], git(ROOT, 'rev-parse', 'HEAD'))
            before, _ = release
        urls = changed_urls(before, all_pages=args.all)
        print(f'IndexNow: {len(urls)} changed/current/removed public URLs selected.')
        if args.dry_run:
            print('\n'.join(urls))
        elif urls:
            submit(urls, verification_key())
        else:
            print('No changed pages to notify.')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, ET.ParseError, KeyError) as error:
        print(f'IndexNow failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
