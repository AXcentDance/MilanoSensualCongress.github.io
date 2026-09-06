import os
import re
import sys
from site_files import site_pages

ROOT_DIR = "."
IT_DIR = "it"

# Pages allowed a deliberate og:title that diverges from <title>
# (SERP-vs-social divergence). Repo-relative paths with forward slashes,
# e.g. "news/some-article.html". Empty by default.
OG_TITLE_DIVERGENCE_ALLOWLIST = set()

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
        if t != ot and ot not in t \
                and rel_path.replace(os.sep, '/') not in OG_TITLE_DIVERGENCE_ALLOWLIST:
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
    
    for path in site_pages():
        if path == '404.html':
            continue
        file_issues = check_file(path, 'it_IT' if path.startswith('it/') else 'en_US')
        if file_issues:
            print(f"{path:<40} | Found {len(file_issues)} issues:")
            for issue in file_issues:
                print(f"  - {issue}")
            total_issues += len(file_issues)

    if total_issues == 0:
        print("\n✅ All Open Graph tags are consistent and valid.")
    else:
        print(f"\n⚠️ Found {total_issues} total OG issues.")
    return 1 if total_issues else 0

if __name__ == "__main__":
    sys.exit(audit_og_tags())
