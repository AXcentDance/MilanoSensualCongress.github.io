import os
import re

ROOT_DIR = "."

def check_image_seo():
    print(f"{'File':<40} | {'Issue':<40} | {'Details'}")
    print("-" * 120)
    
    issues_count = 0
    
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root:
            continue
            
        for file in files:
            if not file.endswith(".html"):
                continue
                
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, ROOT_DIR)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            img_tags = re.findall(r'<img\s+([^>]+)>', content, re.IGNORECASE)
            
            for attrs in img_tags:
                alt_match = re.search(r'alt=["\'](.*?)["\']', attrs, re.IGNORECASE)
                src_match = re.search(r'src=["\'](.*?)["\']', attrs, re.IGNORECASE)
                
                src = src_match.group(1) if src_match else "UNKNOWN_SRC"
                
                if "facebook.com/tr" in src:
                    continue
                
                if not alt_match:
                    print(f"{rel_path:<40} | Missing Alt Text              | Src: {src[:30]}")
                    issues_count += 1
                elif not alt_match.group(1).strip():
                    print(f"{rel_path:<40} | Empty Alt Text                | Src: {src[:30]}")
                    issues_count += 1
                    
                if not src:
                    print(f"{rel_path:<40} | Empty Src                     | Image tag has no source")
                    issues_count += 1
                    continue
                    
                src_clean = src.split('?')[0].lower()
                
                if not src_clean.endswith('.webp') and not src_clean.endswith('/webp') and not src_clean.endswith('.svg') and not src.startswith('data:'):
                    print(f"{rel_path:<40} | Legacy Format (Not WebP)      | Src: {src[:30]}")
                    issues_count += 1

    print("-" * 120)
    print(f"Total potential SEO improvements found: {issues_count}")

if __name__ == "__main__":
    check_image_seo()
