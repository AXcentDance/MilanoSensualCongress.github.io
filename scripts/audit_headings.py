import os
import re
import sys
from html.parser import HTMLParser

class HeadingAuditor(HTMLParser):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.headings = []
        self.errors = []
        self.in_heading = False
        self.current_heading_level = 0
        self.current_heading_text = ""

    def handle_starttag(self, tag, attrs):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.in_heading = True
            self.current_heading_level = int(tag[1])
            self.current_heading_text = ""

    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.in_heading: # ensure we were tracking this
                self.headings.append((self.current_heading_level, self.current_heading_text.strip()))
                self.in_heading = False

    def handle_data(self, data):
        if self.in_heading:
            self.current_heading_text += data

    def audit(self):
        if not self.headings:
            self.errors.append("No headings found.")
            return

        h1_count = len([h for h in self.headings if h[0] == 1])
        if h1_count == 0:
            self.errors.append("Missing <h1> tag.")
        elif h1_count > 1:
            self.errors.append(f"Found {h1_count} <h1> tags. Should be exactly one.")

        # Check hierarchy
        # A heading level can be <= previous level + 1
        # e.g. H2 -> H3 is ok (2 -> 3, diff 1), H2 -> H2 is ok, H3 -> H2 is ok.
        # H2 -> H4 is NOT ok (2 -> 4, diff 2).
        
        # Start checking from the first heading. 
        # Usually first heading should be H1, but we already warn if missing.
        
        previous_level = 0 
        
        for level, text in self.headings:
            # Only check skips if we have a previous level (and usually first tag establishes context)
            if previous_level != 0:
                if level > previous_level + 1:
                    self.errors.append(f"Skipped heading level: H{previous_level} -> H{level} ('{text}')")
            
            previous_level = level

def check_files(directory):
    html_files = []
    for root, dirs, files in os.walk(directory):
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))

    has_errors = False
    for file_path in html_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            auditor = HeadingAuditor(file_path)
            auditor.feed(content)
            auditor.audit()
            
            if auditor.errors:
                print(f"Issues in {file_path}:")
                for err in auditor.errors:
                    print(f"  - {err}")
                has_errors = True
            # else:
            #    print(f"OK: {file_path}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    if not has_errors:
        print("Heading structure audit passed!")

if __name__ == "__main__":
    check_files(".")
