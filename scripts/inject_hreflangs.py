import os
import re

ROOT_DIR = "."
IT_DIR = os.path.join(ROOT_DIR, 'it')

DOMAIN = "https://www.milanosensualcongress.com"

def get_corresponding_path(filename, lang):
    """
    Returns the absolute URL for a given filename and language version.
    """
    base = os.path.basename(filename)
    
    if lang == 'en':
        if base == 'index.html':
            return f"{DOMAIN}/"
        clean = base.replace('.html', '')
        return f"{DOMAIN}/{clean}"
        
    elif lang == 'it':
        if base == 'index.html':
            return f"{DOMAIN}/it/"
        clean = base.replace('.html', '')
        return f"{DOMAIN}/it/{clean}"
    
    return None

def inject_hreflangs():
    print("Starting Hreflang Injection...")
    
    en_files = {f for f in os.listdir(ROOT_DIR) if f.endswith('.html')}
    it_files = {f for f in os.listdir(IT_DIR) if f.endswith('.html')}
    
    all_pages = en_files.union(it_files)
    
    files_changed = 0
    
    for page in all_pages:
        has_en = page in en_files
        has_it = page in it_files
        
        tags = []
        
        # 1. EN Link
        if has_en:
            url_en = get_corresponding_path(page, 'en')
            tags.append(f'<link rel="alternate" hreflang="en" href="{url_en}" />')
            tags.append(f'<link rel="alternate" hreflang="x-default" href="{url_en}" />')
            
        # 2. IT Link
        if has_it:
            url_it = get_corresponding_path(page, 'it')
            tags.append(f'<link rel="alternate" hreflang="it" href="{url_it}" />')
            
        block = "\n  ".join(tags)
        
        if has_en:
            path = os.path.join(ROOT_DIR, page)
            if process_file(path, block):
                files_changed += 1
            
        if has_it:
            path = os.path.join(IT_DIR, page)
            if process_file(path, block):
                files_changed += 1

    print(f"Finished. Updated {files_changed} files.")

def process_file(filepath, new_block):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False
    
    content_clean = re.sub(r'\s*<link rel="alternate" hreflang="[^"]+" href="[^"]+" />', '', content)
    
    # Ideally after <link rel="canonical" ...>
    if '<link rel="canonical"' in content_clean:
         pattern = r'(<link rel="canonical" href="[^"]+">)'
         replacement = r'\1\n  ' + new_block
         new_content = re.sub(pattern, replacement, content_clean)
    else:
        # Insert before </head>
        new_content = content_clean.replace('</head>', f'{new_block}\n</head>')
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

if __name__ == "__main__":
    inject_hreflangs()
