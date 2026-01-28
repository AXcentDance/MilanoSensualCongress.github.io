import os
import sys
from html.parser import HTMLParser

ROOT_DIR = "."

class SyntaxChecker(HTMLParser):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.stack = []
        self.errors = []
        self.void_elements = {
            'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 
            'link', 'meta', 'param', 'source', 'track', 'wbr'
        }

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_elements:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.void_elements:
            return

        if not self.stack:
            self.errors.append(f"Line {self.getpos()[0]}: Stray closing tag </{tag}> found (no matching opening tag).")
            return

        top_tag, top_pos = self.stack[-1]
        
        if top_tag == tag:
            self.stack.pop()
        else:
            if any(t == tag for t, _ in self.stack):
                found_index = -1
                for i in range(len(self.stack) - 1, -1, -1):
                    if self.stack[i][0] == tag:
                        found_index = i
                        break
                
                for i in range(len(self.stack) - 1, found_index, -1):
                    unclosed_tag, unclosed_pos = self.stack[i]
                    self.errors.append(f"Line {unclosed_pos[0]}: Unclosed tag <{unclosed_tag}> (closed by </{tag}> on line {self.getpos()[0]}).")
                
                self.stack = self.stack[:found_index]
            else:
                self.errors.append(f"Line {self.getpos()[0]}: Stray closing tag </{tag}> (expected </{top_tag}>).")

    def check(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.feed(content)
            
            if self.stack:
                for tag, pos in self.stack:
                    self.errors.append(f"Line {pos[0]}: Unclosed tag <{tag}> at end of file.")
                    
        except Exception as e:
            self.errors.append(f"Error parsing file: {str(e)}")
            
        return self.errors

def check_structure(root_dir=ROOT_DIR):
    print(f"Starting Strict HTML Syntax Check in {os.path.abspath(root_dir)}...\n")
    found_errors = False
    
    for root, _, files in os.walk(root_dir):
        if "node_modules" in root or ".git" in root or "scripts" in root:
            continue
            
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                checker = SyntaxChecker(path)
                errors = checker.check()
                
                if errors:
                    found_errors = True
                    print(f"❌ {os.path.relpath(path, root_dir)}:")
                    for error in errors:
                        print(f"  - {error}")
                    print("")
    
    if not found_errors:
        print("✅ No syntax errors found in HTML files.")

if __name__ == "__main__":
    check_structure()
