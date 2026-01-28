import os
import re
import sys

def check_images(directory):
    html_files = []
    for root, dirs, files in os.walk(directory):
        if 'node_modules' in dirs:
            dirs.remove('node_modules') # Skip node_modules
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))

    errors_found = False
    
    # Regex to find img tags
    # This is a simple regex and might not catch all edge cases, but suffices for standard HTML
    img_pattern = re.compile(r'<img([^>]*)>', re.IGNORECASE)
    src_pattern = re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE)
    alt_pattern = re.compile(r'alt=["\']([^"\']*)["\']', re.IGNORECASE)

    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        matches = img_pattern.finditer(content)
        for match in matches:
            attrs = match.group(1)
            
            # Check src
            src_match = src_pattern.search(attrs)
            if src_match:
                src = src_match.group(1)
                # Ignore external images or data URIs for optimization validity if desired, 
                # but user said "all images... in webp".
                # We'll flag non-webp unless it seems to be an external tracking pixel or something.
                if not src.lower().endswith('.webp') and not src.startswith(('http', 'https', 'data:')):
                    print(f"[FAIL] Non-WebP Image in {file_path}: {src}")
                    errors_found = True
            
            # Check alt
            alt_match = alt_pattern.search(attrs)
            if not alt_match:
                print(f"[FAIL] Missing Alt Text in {file_path}: <img {attrs.strip()} ... >")
                errors_found = True
            elif not alt_match.group(1).strip():
                print(f"[FAIL] Empty Alt Text in {file_path}: src={src_match.group(1) if src_match else 'unknown'}")
                errors_found = True

    if errors_found:
        sys.exit(1)
    else:
        print("All images are optimized!")
        sys.exit(0)

if __name__ == "__main__":
    check_images(".")
