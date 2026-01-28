import os
import subprocess
import re

ROOT_DIR = "."

def convert_and_update():
    print("Scanning for images to convert to WebP...")
    
    # 1. Gather all images referenced in HTML
    images_to_convert = set()
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root:
            continue
            
        for file in files:
            if not file.endswith(".html"):
                continue
                
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find img src
            matches = re.findall(r'src=["\']([^"\']+\.(?:jpg|jpeg|png))["\']', content, re.IGNORECASE)
            for m in matches:
                # Resolve to absolute path
                if m.startswith('/'):
                    abs_path = os.path.join(os.path.abspath(ROOT_DIR), m.lstrip('/'))
                else:
                    abs_path = os.path.join(os.path.dirname(os.path.abspath(filepath)), m)
                
                if os.path.exists(abs_path):
                    images_to_convert.add(abs_path)

    print(f"Found {len(images_to_convert)} unique images to convert.")

    converted_count = 0
    
    for src_path in images_to_convert:
        base, ext = os.path.splitext(src_path)
        dst_path = base + ".webp"
        
        if os.path.exists(dst_path):
            # Already exists, verify HTML references later
            pass
        else:
            # Convert
            print(f"Converting: {os.path.relpath(src_path, ROOT_DIR)} -> .webp")
            try:
                subprocess.check_call(['cwebp', '-q', '80', src_path, '-o', dst_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                converted_count += 1
            except FileNotFoundError:
                print("Error: cwebp not found. Please install webp tools.")
                return
            except subprocess.CalledProcessError as e:
                print(f"Error converting {src_path}: {e}")
                continue

    # 2. Update HTML References
    print("Updating HTML references...")
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root:
            continue
            
        for file in files:
            if not file.endswith(".html"):
                continue
                
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Simple replace strategy: exact filename match to safe relative path issues?
            # Or regex replace?
            # Let's use regex to be safe we only replace inside src attributes or similar
            # Actually, standard replace of basename might be risky if same filename in different dirs.
            # But we generated the list from HTML references, so we know they are used.
            
            # Better: iterate over the images we found/converted.
            
            for src_path in images_to_convert:
                filename_old = os.path.basename(src_path)
                filename_new = os.path.splitext(filename_old)[0] + ".webp"
                
                # We need to replace references to this file.
                # Regex: src=".../filename.jpg" -> src=".../filename.webp"
                # Be careful not to replace partial matches.
                
                pattern = re.compile(re.escape(filename_old) + r'(?=["\'])', re.IGNORECASE)
                content = pattern.sub(filename_new, content)
                
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {file}")

    print(f"Done. Converted {converted_count} images.")

if __name__ == "__main__":
    convert_and_update()
