import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def audit_assets():
    print("## Asset Integrity Audit")
    print(f"Checking for broken images/videos in {ROOT_DIR}...")
    
    issues = []
    
    # Walk all directories
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root:
            continue
            
        for file in files:
            if not file.endswith('.html'):
                continue
                
            filepath = os.path.join(root, file)
            rel_dir = os.path.dirname(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regex for src="..."
            src_matches = re.finditer(r'src=["\']([^"\']+)["\']', content)
            
            for match in src_matches:
                src = match.group(1)
                
                # Skip absolute URLs (http, https, //) or data/mailto
                if src.startswith(('http', '//', 'data:', 'mailto:')):
                    continue
                
                check_path = None
                if src.startswith('/'):
                    # Absolute path relative to root
                    check_path = os.path.join(ROOT_DIR, src.lstrip('/'))
                else:
                    # Relative path
                    check_path = os.path.join(rel_dir, src)
                
                # Remove query params and anchors
                check_path = check_path.split('?')[0]
                check_path = check_path.split('#')[0]
                
                if not os.path.exists(check_path):
                    issues.append(f"[{os.path.relpath(filepath, ROOT_DIR)}] Broken Asset: {src}")
                    
            # Check CSS url(...)
            css_matches = re.finditer(r'url\([\"\']?([^)\"\']+)[\"\']?\)', content)
            for match in css_matches:
                url = match.group(1)
                if url.startswith(('http', '//', 'data:')):
                    continue
                    
                check_path = None
                if url.startswith('/'):
                     check_path = os.path.join(ROOT_DIR, url.lstrip('/'))
                else:
                     check_path = os.path.join(rel_dir, url)
                     
                check_path = check_path.split('?')[0]
                check_path = check_path.split('#')[0]
                
                if not os.path.exists(check_path):
                     issues.append(f"[{os.path.relpath(filepath, ROOT_DIR)}] Broken CSS Asset: {url}")

    if issues:
        print(f"⚠️ Found {len(issues)} broken assets:")
        for i in issues:
            print(i)
        sys.exit(1)
    else:
        print("✅ All assets link correctly.")
        sys.exit(0)

import sys
if __name__ == "__main__":
    audit_assets()
