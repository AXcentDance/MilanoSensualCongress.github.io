import os
import re
from urllib.parse import unquote
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Correct ROOT_DIR to be the repo root, assuming script is in scripts/
if not os.path.exists(os.path.join(ROOT_DIR, "index.html")):
    # Fallback if script run from root
    if os.path.exists("index.html"):
        ROOT_DIR = os.getcwd()

def check_broken_links():
    print(f"Checking for broken internal links in {ROOT_DIR}...")
    print("-" * 60)

    # First, gather all existing files to validate against
    all_files = set()
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            all_files.add(os.path.abspath(path))
            
    issues_found = 0
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root:
            continue
            
        for file in files:
            if not file.endswith(".html"):
                continue
                
            source_path = os.path.join(root, file)
            
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all hrefs
            links = re.findall(r'href=["\'](.*?)["\']', content)
            
            for link in links:
                # Skip external links, anchors only, mailto, tel
                if link.startswith(("http", "//", "mailto:", "tel:", "#")):
                    continue
                
                # Skip brackets/weird replacements mostly found in templates
                if "{" in link or "}" in link: 
                    continue

                # Skip common static assets we know exist or don't want to check rigorously here
                # Also skip cdn links if any missed by http check
                # User's script skipped: .css, .png, .jpg, .webp, .ico, .js
                if link.endswith((".css", ".png", ".jpg", ".webp", ".ico", ".js", ".svg", ".mp4")):
                    continue
                    
                # Clean link (remove hash for file check)
                link_path = link.split('#')[0]
                
                # Retrieve query params
                link_path = link_path.split('?')[0]  
                
                if not link_path:
                    continue
                    
                # Resolve paths
                if link_path.startswith("/"):
                    target_path = os.path.join(ROOT_DIR, link_path.lstrip("/"))
                else:
                    target_path = os.path.join(root, link_path)
                
                # Check for extensionless links
                target_path_abs = os.path.abspath(target_path)
                target_path_html = target_path_abs
                
                status_exists = False
                
                # Check exact match first (could be a dir or file)
                if os.path.exists(target_path_abs):
                     status_exists = True
                else:
                    # Check if it's a directory (might be missing trailing slash in link but resolving to dir)
                    # or link is /foo/bar and we have /foo/bar.html
                    if not target_path_abs.endswith(".html"):
                         # Try adding .html
                         if os.path.exists(target_path_abs + ".html"):
                             status_exists = True
                
                if not status_exists:
                    # One last check: might be a directory with index.html
                    # If target_path_abs is intended to be a dir but os.exits failed? 
                    # Actually if os.exists failed, it's not a dir.
                    pass

                if not status_exists:
                    print(f"[BROKEN] In {file}: link to '{link}'")
                    issues_found += 1

    if issues_found == 0:
        print("Success! No broken internal links found.")
        sys.exit(0)
    else:
        print(f"\nFound {issues_found} broken links.")
        sys.exit(1)

if __name__ == "__main__":
    check_broken_links()
