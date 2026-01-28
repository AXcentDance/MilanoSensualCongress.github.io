import os
import re
import datetime
from urllib.parse import quote, urljoin
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    
ROOT_DIR = "."
DOMAIN = 'https://www.milanosensualcongress.com'

def is_noindex(filepath):
    """Checks if a file has <meta name="robots" content="noindex...">"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if re.search(r'<meta\s+name=["\']robots["\']\s+content=["\'].*?noindex.*?["\']', content, re.IGNORECASE):
            return True
    except Exception:
        return False
    return False

def get_lastmod(filepath):
    """Returns file modification time in YYYY-MM-DD format."""
    try:
        timestamp = os.path.getmtime(filepath)
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except Exception:
        return datetime.datetime.now().strftime('%Y-%m-%d')

def get_url_path(filepath):
    """Converts filesystem path to URL path."""
    rel_path = os.path.relpath(filepath, ROOT_DIR)
    
    # Handle Windows backslashes
    rel_path = rel_path.replace(os.sep, '/')
    
    # Remove .html extension for clean URLs
    if rel_path.endswith('.html'):
        rel_path = rel_path[:-5]
        
    if rel_path == 'index':
        return '/'
    if rel_path == 'it/index':
        return '/it/'
    if rel_path == 'spring/index':
        return '/spring/'
    
    return '/' + rel_path

def get_page_images(filepath):
    """Extracts images from an HTML file for sitemap."""
    images = []
    if not HAS_BS4:
        return images
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
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
            
    except Exception as e:
        # print(f"Error parsing images for {filepath}: {e}")
        pass
        
    return images

def generate_sitemap():
    print("Generating sitemap.xml...")
    
    all_files = []
    for root, dirs, files in os.walk(ROOT_DIR):
        if 'scripts' in dirs: dirs.remove('scripts')
        if '.git' in dirs: dirs.remove('.git')
        if 'node_modules' in dirs: dirs.remove('node_modules')
        
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if not is_noindex(filepath):
                    all_files.append(filepath)

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
            
            # Priority
            if key in ['index.html', 'index']:
                priority = '1.0'
            elif key.startswith('spring'):
                priority = '0.9'
            else:
                priority = '0.8'
                
            xml_output += '  <url>\n'
            xml_output += f'    <loc>{url}</loc>\n'
            xml_output += f'    <lastmod>{lastmod}</lastmod>\n'
            xml_output += f'    <priority>{priority}</priority>\n'
            
            # Hreflang
            if 'en' in variants:
                en_url = DOMAIN + get_url_path(variants['en'])
                xml_output += f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}" />\n'
                xml_output += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_url}" />\n'
            
            if 'it' in variants:
                it_url = DOMAIN + get_url_path(variants['it'])
                xml_output += f'    <xhtml:link rel="alternate" hreflang="it" href="{it_url}" />\n'
                
            # Images
            page_images = get_page_images(filepath)
            for img in page_images:
                xml_output += '    <image:image>\n'
                xml_output += f'      <image:loc>{img["loc"]}</image:loc>\n'
                if 'title' in img:
                    safe_title = img['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", "&apos;")
                    xml_output += f'      <image:title>{safe_title}</image:title>\n'
                xml_output += '    </image:image>\n'
                
            xml_output += '  </url>\n'

    xml_output += '</urlset>'
    
    output_path = os.path.join(ROOT_DIR, 'sitemap.xml')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_output)
    
    print(f"Sitemap generated at {output_path} with {len(all_files)} URLs.")

if __name__ == "__main__":
    generate_sitemap()
