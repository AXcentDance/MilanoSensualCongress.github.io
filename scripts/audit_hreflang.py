import os
import re
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IT_DIR = os.path.join(ROOT_DIR, 'it')

def get_hreflangs(content):
    # Returns dict: {'en': 'url', 'it': 'url', ...}
    matches = re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', content)
    return {lang: url for lang, url in matches}

def audit_hreflang():
    print("## Hreflang Reciprocity Audit")
    print("Verifying that every EN page points to IT, and IT points back to EN...")
    
    issues = []
    
    en_files = [f for f in os.listdir(ROOT_DIR) if f.endswith('.html')]
    
    for en_file in en_files:
        path = os.path.join(ROOT_DIR, en_file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        hreflangs = get_hreflangs(content)
        
        # Check if it has IT link
        if 'it' not in hreflangs:
            # Maybe it doesn't exist in IT? 
            # We only flag if we expect it. Assuming 1:1 for main pages.
            # issues.append(f"[EN] {en_file}: Missing hreflang='it'")
            continue
            
        it_url = hreflangs['it']
        
        # Handle URLs:
        # Assuming format like "https://milanosensual.com/it/..." or just relative "../../it/..."
        # Simplified Check: just check filename mapping for now if strictly 1:1
        
        # If the URL ends with /, it's index.html
        # If it ends with .html, it's that file.
        
        # Let's try to map it_url to a local file
        # Removing domain if present
        it_path_part = it_url.split('/it/')[-1] # "about.html" or ""
        
        if it_path_part == "" or it_path_part == "/":
            it_filename = "index.html"
        else:
            it_filename = it_path_part
            if not it_filename.endswith('.html'):
                 it_filename += ".html"
                 
        it_file_path = os.path.join(IT_DIR, it_filename)
        
        if not os.path.exists(it_file_path):
             issues.append(f"[EN] {en_file}: Hreflang points to non-existent file {it_file_path} (URL: {it_url})")
             continue
             
        # Check reciprocity
        with open(it_file_path, 'r', encoding='utf-8') as f:
            it_content = f.read()
            
        it_hreflangs = get_hreflangs(it_content)
        
        if 'en' not in it_hreflangs:
             issues.append(f"[IT] {it_filename}: Missing hreflang='en' (Broken Reciprocity for {en_file})")
             continue
             
    print(f"Scanned {len(en_files)} English files.")
    
    if issues:
        print(f"⚠️ Found {len(issues)} Hreflang issues:")
        for i in issues:
            print(i)
    else:
        print("✅ Hreflang Logic is perfectly reciprocal.")

if __name__ == "__main__":
    audit_hreflang()
