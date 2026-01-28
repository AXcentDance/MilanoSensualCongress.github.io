import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT_DIR = "."

class LinkAuditor(HTMLParser):
    def __init__(self, filepath, root_dir):
        super().__init__()
        self.filepath = filepath
        self.root_dir = root_dir
        self.broken_links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href')
            
            if not href:
                return
                
            # Skip externals, anchors, mailto, tel, javascript
            if href.startswith(('http', '//', '#', 'mailto:', 'tel:', 'javascript:')):
                return
                
            # Handle in-page anchors with path e.g. "index.html#contact"
            href_clean = href.split('#')[0]
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
            
            if not exists:
                self.broken_links.append({
                    'link': href,
                    'resolved_to': os.path.relpath(target_path, self.root_dir)
                })

def audit_relative_links():
    print(f"Starting Relative Link Audit in {os.path.abspath(ROOT_DIR)}...\n")
    
    all_broken = []
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if 'node_modules' in dirs: dirs.remove('node_modules')
        if '.git' in dirs: dirs.remove('.git')
        if 'scripts' in dirs: dirs.remove('scripts')
            
        for file in files:
            if not file.endswith('.html'):
                continue
                
            source_path = os.path.join(root, file)
            
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                auditor = LinkAuditor(source_path, ROOT_DIR)
                auditor.feed(content)
                
                if auditor.broken_links:
                    relative_source = os.path.relpath(source_path, ROOT_DIR)
                    for issue in auditor.broken_links:
                        all_broken.append({
                            'source': relative_source,
                            'link': issue['link'],
                            'missing': issue['resolved_to']
                        })
                        
            except Exception as e:
                print(f"Error parsing {source_path}: {e}")

    # Report
    if all_broken:
        print(f"FOUND {len(all_broken)} BROKEN INTERNAL LINKS:\n")
        for issue in all_broken:
            print(f"FILE: {issue['source']}")
            print(f"  LINK:   {issue['link']}")
            print(f"  MISSING: {issue['missing']}")
            print("-" * 40)
        sys.exit(1)
    else:
        print("SUCCESS: No broken relative links found!")
        sys.exit(0)

if __name__ == "__main__":
    audit_relative_links()
