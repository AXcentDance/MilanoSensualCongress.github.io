import os
import re
import json
import sys

ROOT_DIR = "."

def audit_schema():
    print("## Schema Audit")
    print(f"Verifying JSON-LD schemas in {os.path.abspath(ROOT_DIR)}...")
    
    issues = []
    
    html_files = []
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root:
            continue
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    for filepath in html_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find JSON-LD blocks
        matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL)
        
        if not matches:
            # Not all pages need schema, maybe just index/product/event pages.
            # print(f"[{os.path.relpath(filepath, ROOT_DIR)}] Info: No Schema found.")
            continue
            
        for i, json_str in enumerate(matches):
            try:
                data = json.loads(json_str)
                # print(f"[{os.path.relpath(filepath, ROOT_DIR)}] ✅ Valid JSON-LD Schema found.")
            except json.JSONDecodeError as e:
                issues.append(f"[{os.path.relpath(filepath, ROOT_DIR)}] Invalid JSON-LD Schema: {e}")

    if issues:
        print(f"⚠️ Found {len(issues)} Schema issues:")
        for i in issues:
            print(i)
        sys.exit(1)
    else:
        print("✅ JSON-LD Schemas are valid JSON.")

if __name__ == "__main__":
    audit_schema()
