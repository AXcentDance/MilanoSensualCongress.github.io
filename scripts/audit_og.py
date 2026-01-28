import os
import re

ROOT_DIR = "."
IT_DIR = "it"

def check_file(filepath, expected_locale):
    issues = []
    rel_path = os.path.relpath(filepath, ROOT_DIR)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Extract standard tags
    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.S)
    meta_desc_match = re.search(r'<meta name="description"\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
    
    # Extract OG tags
    og_title_match = re.search(r'<meta property="og:title"\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
    og_desc_match = re.search(r'<meta property="og:description"\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
    og_locale_match = re.search(r'<meta property="og:locale"\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
    
    # 1. Check Locale
    if not og_locale_match:
        issues.append(f"Missing og:locale")
    else:
        found_locale = og_locale_match.group(1)
        if found_locale != expected_locale:
            issues.append(f"Invalid og:locale: '{found_locale}'. Expected '{expected_locale}'")

    # 2. Check Title Presence & Parity
    if not og_title_match:
        issues.append("Missing og:title")
    elif title_match:
        t = title_match.group(1).strip()
        ot = og_title_match.group(1).strip()
        # Loose check: OG title should be contained in or equal to Title, or vice versa
        # Often Title has branding suffix "| Milano Sensual..."
        if t != ot and ot not in t:
             # Just a warning or note? User asked for mismatch check.
             issues.append(f"Title vs OG Title mismatch.\n      Title: {t}\n      OG:    {ot}")

    # 3. Check Description Presence & Parity
    if not og_desc_match:
        # It's okay if meta desc is missing too? simpler to just flag missing OG.
        issues.append("Missing og:description")
    elif meta_desc_match:
        d = meta_desc_match.group(1).strip()
        od = og_desc_match.group(1).strip()
        if d != od:
             issues.append(f"Description vs OG Description mismatch.\n      Meta: {d[:50]}...\n      OG:   {od[:50]}...")

    return issues

def audit_og_tags():
    print("## Open Graph Audit")
    print(f"{'File':<40} | {'Issues'}")
    print("-" * 100)
    
    total_issues = 0
    
    # 1. Check English (Root)
    for root, dirs, files in os.walk(ROOT_DIR):
        if ".git" in root or "node_modules" in root or "scripts" in root or "it" in root.split(os.sep) or "spring" in root.split(os.sep):
            continue
        # Only direct root children or non-lang subfolders if any
        # Assuming EN is root.
        
        for file in files:
            if file.endswith('.html') and file != '404.html':
                 path = os.path.join(root, file)
                 file_issues = check_file(path, "en_US")
                 if file_issues:
                     print(f"{os.path.relpath(path, ROOT_DIR):<40} | Found {len(file_issues)} issues:")
                     for i in file_issues:
                         print(f"{'':<40} | - {i}")
                     total_issues += len(file_issues)

    # 2. Check Italian (it/)
    if os.path.exists(IT_DIR):
        for root, dirs, files in os.walk(IT_DIR):
            for file in files:
                if file.endswith('.html'):
                    path = os.path.join(root, file)
                    file_issues = check_file(path, "it_IT")
                    if file_issues:
                        print(f"{os.path.relpath(path, ROOT_DIR):<40} | Found {len(file_issues)} issues:")
                        for i in file_issues:
                            print(f"{'':<40} | - {i}")
                        total_issues += len(file_issues)

    if total_issues == 0:
        print("\n✅ All Open Graph tags are consistent and valid.")
    else:
        print(f"\n⚠️ Found {total_issues} total OG issues.")

if __name__ == "__main__":
    audit_og_tags()
