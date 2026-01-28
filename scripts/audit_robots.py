import os
import re

ROOT_DIR = "."

def check_robots(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)["\']', content, re.IGNORECASE)
    if match:
        return match.group(1)
    return "AG (Allowed/Index)" # Default if missing

def main():
    print(f"{'File':<50} | {'Robots Status':<20}")
    print("-" * 80)
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if 'scripts' in dirs:
            dirs.remove('scripts')
        if '.git' in dirs:
            dirs.remove('.git')
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
            
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, ROOT_DIR)
                status = check_robots(path)
                
                print(f"{rel_path:<50} | {status:<20}")

if __name__ == "__main__":
    main()
