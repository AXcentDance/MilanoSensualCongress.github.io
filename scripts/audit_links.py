import os
from site_files import site_pages
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

ROOT_DIR = "."

class LinkAuditor(HTMLParser):
    def __init__(self, filepath, root_dir):
        super().__init__()
        self.filepath = filepath
        self.root_dir = root_dir
        self.broken_links = []

    def handle_starttag(self, tag, attrs):
        # Include head links and other href-bearing elements, preserving the
        # useful coverage of the retired report-only link audit.
        if any(name == 'href' for name, _value in attrs):
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href')
            
            if not href:
                return
                
            # Skip externals, anchors, mailto, tel, javascript
            if href.startswith(('http', '//', '#', 'mailto:', 'tel:', 'javascript:')):
                return
                
            # Handle in-page anchors with path e.g. "index.html#contact"
            href_clean = unquote(urlparse(href).path)
            if not href_clean: # Was just "#" or "#something"
                return
            
            # Resolve path
            source_dir = os.path.dirname(self.filepath)
            
            # Handle root-relative paths
            if href_clean.startswith('/'):
                 target_path = os.path.join(self.root_dir, href_clean.lstrip('/'))
            else:
                 target_path = os.path.join(source_dir, href_clean)
            
            # Normalize (resolve ../)
            target_path = os.path.normpath(target_path)
            
            # Check existence
            # We assume it links to a file. If it links to a dir, we might check for index.html?
            # Standard static sites usually link to .html explicitly or a dir with index.html
            
            exists = False
            if os.path.exists(target_path):
                if os.path.isdir(target_path):
                     if os.path.exists(os.path.join(target_path, 'index.html')):
                         exists = True
                else:
                    exists = True
            
            # Check for clean URLs (path -> path.html)
            if not exists and not target_path.endswith('.html'):
                if os.path.exists(target_path + '.html'):
                    exists = True
            
            if not exists:
                self.broken_links.append({
                    'link': href,
                    'resolved_to': os.path.relpath(target_path, self.root_dir)
                })

def audit_relative_links(root_dir=ROOT_DIR):
    print(f"Starting Relative Link Audit in {os.path.abspath(root_dir)}...\n")
    
    all_broken = []
    
    for page in site_pages(root_dir):
        source_path = os.path.join(root_dir, page)
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            auditor = LinkAuditor(source_path, root_dir)
            auditor.feed(content)
            for issue in auditor.broken_links:
                all_broken.append({
                    'source': page,
                    'link': issue['link'],
                    'missing': issue['resolved_to']
                })
        except Exception as e:
            all_broken.append({'source': page, 'link': '(page could not be checked)',
                               'missing': str(e)})

    # Report
    if all_broken:
        print(f"FOUND {len(all_broken)} BROKEN INTERNAL LINKS:\n")
        for issue in all_broken:
            print(f"FILE: {issue['source']}")
            print(f"  LINK:   {issue['link']}")
            print(f"  MISSING: {issue['missing']}")
            print("-" * 40)
        return 1
    else:
        print("SUCCESS: No broken relative links found!")
        return 0

if __name__ == "__main__":
    sys.exit(audit_relative_links())
