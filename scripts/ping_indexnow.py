"""Notify IndexNow about changed public pages only after a successful release."""
import json
import os
import subprocess
from urllib.request import Request, urlopen
from site_files import site_pages

DOMAIN = 'https://milanosensualcongress.com'


def changed_urls(before):
    if not before or set(before) == {'0'}:
        return []
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', before, 'HEAD', '--', '*.html'], text=True).splitlines()
    pages = set(site_pages()) - {'404.html'}
    return [DOMAIN + '/' + (file[:-10] if file.endswith('index.html') else file[:-5])
            for file in changed if file in pages]


if __name__ == '__main__':
    urls = changed_urls(os.environ.get('BEFORE'))
    if urls:
        key = os.environ['INDEXNOW_KEY']
        payload = {'host': 'milanosensualcongress.com', 'key': key,
                   'keyLocation': f'{DOMAIN}/{key}.txt', 'urlList': urls}
        request = Request('https://api.indexnow.org/indexnow',
                          data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json; charset=utf-8'})
        with urlopen(request, timeout=30) as response:
            print(f'IndexNow HTTP {response.status}: {len(urls)} changed pages')
    else:
        print('No changed pages to notify')
