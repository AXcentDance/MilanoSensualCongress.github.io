import os
import re

ROOT_DIR = "."

def fix_links(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return
    
    original_content = content
    
    # regex to find hrefs that might need fixing
    # strict capture of href value
    def replace_callback(match):
        full_match = match.group(0)
        quote = match.group(1)
        href = match.group(2)
        
        if href.startswith(('http', '//', '#', 'mailto:', 'tel:', 'javascript:')):
            return full_match
            
        if href.endswith('/') or href.endswith('.html'):
            return full_match

        # Potential missing extension
        # Check if it exists as a .html file matching the relative path
        
        # Resolve path relative to current file
        file_dir = os.path.dirname(filepath)
        if href.startswith('/'):
            target_path = os.path.join(ROOT_DIR, href.lstrip('/'))
        else:
            target_path = os.path.join(file_dir, href)
            
        # Check if target + .html exists
        candidate = target_path + ".html"
        if os.path.exists(candidate) and not os.path.isdir(target_path):
             return f'href={quote}{href}.html{quote}'
             
        return full_match

    # Pattern: href=("|')([^"']+)("|')
    # Using sub with function
    new_content = re.sub(r'href=(["\'])([^"\']+)(["\'])', replace_callback, content)
    
    if new_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed links in: {os.path.relpath(filepath, ROOT_DIR)}")

def main():
    print("Scanning and fixing broken internal links (missing .html extension)...")
    for root, dirs, files in os.walk(ROOT_DIR):
        if 'scripts' in dirs:
            dirs.remove('scripts')
        if '.git' in dirs:
            dirs.remove('.git')
            
        for file in files:
            if file.endswith(".html"):
                fix_links(os.path.join(root, file))

if __name__ == "__main__":
    main()
