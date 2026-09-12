import os
from site_files import classified_pages, page_url_path
import datetime
import subprocess
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr
from generation_support import GenerationError, read_page, run_generator, write_outputs
    
ROOT_DIR = "."
DOMAIN = 'https://milanosensualcongress.com'

def get_lastmod(filepath):
    """Truthful lastmod: newest git commit touching the file (ISO 8601 with
    timezone). Files with uncommitted changes are stamped now. Never hand-edit
    lastmod values — search engines learn to distrust sitemaps that lie.
    NOTE: Use a clone with full history or dates collapse."""
    try:
        dirty = subprocess.run(
            ['git', 'status', '--porcelain', '--', filepath],
            capture_output=True, text=True).stdout.strip()
        if not dirty:
            out = subprocess.run(
                ['git', 'log', '-1', '--format=%cI', '--', filepath],
                capture_output=True, text=True).stdout.strip()
            if out:
                return out
    except Exception:
        pass
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

def get_url_path(filepath):
    """Converts filesystem path to URL path."""
    rel_path = os.path.relpath(filepath, ROOT_DIR)
    
    # Handle Windows backslashes
    rel_path = rel_path.replace(os.sep, '/')
    
    return page_url_path(rel_path)

def get_page_images(filepath, soup=None):
    """Extracts images from an HTML file for sitemap."""
    images = []
    try:
        if soup is None:
            soup = read_page(filepath)
            
        seen_src = set()
        
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
                
            # Skip externals
            if src.startswith(('http', '//', 'data:', 'blob:')):
                continue
                
            # Logic for absolute URL
            # 1. Resolve to file system absolute
            # 2. Convert to domain absolute
            
            # Simple handling for known structures
            img_url = ""
            clean_src = src.split('?')[0]
            
            # Resolve relative ../
            # file: spring/index.html, src: ../images/promo.webp
            # resolved: images/promo.webp
            # url: domain/images/promo.webp
            
            file_dir = os.path.dirname(filepath)
            rel_file_dir = os.path.relpath(file_dir, ROOT_DIR)
            
            if clean_src.startswith('/'):
                 # explicit root relative
                 img_path_rel = clean_src.lstrip('/')
            else:
                 # relative
                 # os.path.join base logic
                 combined = os.path.join(rel_file_dir, clean_src)
                 img_path_rel = os.path.normpath(combined)
            
            # Construct URL
            # Ensure forward slashes
            img_path_rel = img_path_rel.replace(os.sep, '/')
            img_url = f"{DOMAIN}/{img_path_rel}"

            if img_url in seen_src:
                continue
                
            img_data = {
                'loc': img_url
            }
            
            alt = img.get('alt')
            if alt:
                img_data['title'] = alt
                
            images.append(img_data)
            seen_src.add(img_url)
            
    except Exception as error:
        raise GenerationError(f'Cannot extract sitemap images from {filepath}: {error}') from error
        
    return images

def get_hreflang_links(filepath, soup=None):
    """Read explicit hreflang URLs from the page head.

    Translated pages often use different slugs, so filesystem-name matching is
    not sufficient to pair English and Italian URLs in the sitemap.
    """
    links = {}
    try:
        if soup is None:
            soup = read_page(filepath)
        for link in soup.find_all('link', hreflang=True, href=True):
            rel = link.get('rel', [])
            if 'alternate' not in rel:
                continue
            lang = link.get('hreflang', '').lower()
            href = link.get('href', '').strip()
            if lang in {'en', 'it', 'x-default'} and href.startswith(DOMAIN):
                links[lang] = href
    except Exception as error:
        raise GenerationError(f'Cannot extract sitemap language links from {filepath}: {error}') from error
    return links

def generate_sitemap():
    print("Generating sitemap.xml...")
    
    all_files = []
    parsed_pages = {}
    for page, soup, indexable in classified_pages(ROOT_DIR):
        if indexable:
            filepath = os.path.join(ROOT_DIR, page)
            all_files.append(filepath)
            parsed_pages[filepath] = soup

    if not all_files:
        raise GenerationError(f'No indexable HTML pages found under {ROOT_DIR}; refusing to replace existing outputs')

    # Map: key -> {lang: filepath}
    page_map = {}
    
    for filepath in all_files:
        rel_path = os.path.relpath(filepath, ROOT_DIR).replace(os.sep, '/')
        
        if rel_path.startswith('it/'):
            key = rel_path[3:] 
            lang = 'it'
        else:
            key = rel_path
            lang = 'en'
            
        if key not in page_map:
            page_map[key] = {}
        
        page_map[key][lang] = filepath

    xml_output = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_output += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    
    # Sort for stability
    sorted_keys = sorted(page_map.keys())
    
    for key in sorted_keys:
        variants = page_map[key]
        for lang, filepath in variants.items():
            url = DOMAIN + get_url_path(filepath)
            lastmod = get_lastmod(filepath)
            
            xml_output += '  <url>\n'
            xml_output += f'    <loc>{escape(url)}</loc>\n'
            xml_output += f'    <lastmod>{lastmod}</lastmod>\n'
            
            # Prefer the page's explicit hreflang declarations. This preserves
            # language pairing when translated pages use localized slugs.
            explicit_hreflangs = get_hreflang_links(filepath, parsed_pages[filepath])
            if explicit_hreflangs:
                for hreflang in ('en', 'x-default', 'it'):
                    href = explicit_hreflangs.get(hreflang)
                    if href:
                        xml_output += f'    <xhtml:link rel="alternate" hreflang="{hreflang}" href={quoteattr(href)} />\n'
            else:
                if 'en' in variants:
                    en_url = DOMAIN + get_url_path(variants['en'])
                    xml_output += f'    <xhtml:link rel="alternate" hreflang="en" href={quoteattr(en_url)} />\n'
                    xml_output += f'    <xhtml:link rel="alternate" hreflang="x-default" href={quoteattr(en_url)} />\n'

                if 'it' in variants:
                    it_url = DOMAIN + get_url_path(variants['it'])
                    xml_output += f'    <xhtml:link rel="alternate" hreflang="it" href={quoteattr(it_url)} />\n'
                
            # Images
            page_images = get_page_images(filepath, parsed_pages[filepath])
            for img in page_images:
                xml_output += '    <image:image>\n'
                xml_output += f'      <image:loc>{escape(img["loc"])}</image:loc>\n'
                if 'title' in img:
                    safe_title = img['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", "&apos;")
                    xml_output += f'      <image:title>{safe_title}</image:title>\n'
                xml_output += '    </image:image>\n'
                
            xml_output += '  </url>\n'

    xml_output += '</urlset>'
    
    output_path = os.path.join(ROOT_DIR, 'sitemap.xml')
    try:
        ET.fromstring(xml_output)
    except ET.ParseError as error:
        raise GenerationError(f'{output_path}: generated XML is invalid: {error}') from error
    write_outputs({output_path: xml_output})
    
    print(f"Sitemap generated at {output_path} with {len(all_files)} URLs.")

if __name__ == "__main__":
    raise SystemExit(run_generator(generate_sitemap))
