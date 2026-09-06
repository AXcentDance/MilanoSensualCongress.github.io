"""Check image semantics without treating decorative empty alt as an error."""
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from site_files import site_pages


def image_problems(image):
    errors = []
    if not image.has_attr('alt'):
        errors.append('missing alt attribute')
    if not image.get('src', '').strip():
        errors.append('missing image source')
    return errors


def check_image_seo():
    errors = []
    for page in site_pages():
        soup = BeautifulSoup(Path(page).read_text(), 'html.parser')
        for image in soup.find_all('img'):
            src = image.get('src', '')
            errors.extend(f'{page}: {problem}: {src}' for problem in image_problems(image))
            parsed = urlsplit(src)
            extension = Path(parsed.path).suffix.lower()
            if not parsed.scheme and not parsed.netloc:
                file = (Path(parsed.path.lstrip('/')) if parsed.path.startswith('/')
                        else Path(page).parent / parsed.path)
                if not file.is_file():
                    errors.append(f'{page}: image file does not exist: {src}')
                elif extension == '.webp':
                    with file.open('rb') as stream:
                        header = stream.read(12)
                    if header[:4] != b'RIFF' or header[8:12] != b'WEBP':
                        errors.append(f'{page}: file is not encoded as WebP: {src}')
            if extension in ('.jpg', '.jpeg', '.png', '.gif'):
                print(f'WARNING: {page}: consider WebP/AVIF if appropriate for this content image: {src}')
    if errors:
        print('\n'.join(errors))
        return 1
    print('image attributes passed (empty alt is valid for decoration)')
    return 0


if __name__ == '__main__':
    raise SystemExit(check_image_seo())
