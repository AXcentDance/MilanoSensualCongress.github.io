import os
import re

def audit_seo(root_dir):
    print(f"{'File':<50} | {'Title':<40} | {'Description'}")
    print("-" * 150)
    
    for root, dirs, files in os.walk(root_dir):
        if 'node_modules' in root or '.git' in root or '_site' in root or 'scripts' in root:
            continue
            
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, root_dir)
                
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Extract title
                        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                        if title_match:
                            title = title_match.group(1).strip()
                            title = re.sub(r'\s+', ' ', title)
                        else:
                            title = "MISSING"

                        # Extract meta description
                        # Support both single and double quotes, and various attribute orderings
                        desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', content, re.IGNORECASE | re.DOTALL)
                        if not desc_match:
                             desc_match = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', content, re.IGNORECASE | re.DOTALL)

                        if desc_match:
                            desc = desc_match.group(1).strip()
                            desc = re.sub(r'\s+', ' ', desc)
                        else:
                            desc = "MISSING"
                            
                        print(f"{rel_path:<50} | {title[:40]:<40} | {desc}")
                except Exception as e:
                    print(f"{rel_path:<50} | ERROR: {str(e)}")

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(root, 'index.html')):
         root = os.getcwd()
    audit_seo(root)
