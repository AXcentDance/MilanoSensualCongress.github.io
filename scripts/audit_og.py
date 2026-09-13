import os
import re
import sys
from bs4 import BeautifulSoup
from site_files import indexable_pages
from generation_support import GenerationError
from sync_social_meta import CardBuild

ROOT_DIR = "."
IT_DIR = "it"

# Pages allowed a deliberate og:title that diverges from <title>
# (SERP-vs-social divergence). Repo-relative paths with forward slashes,
# e.g. "news/some-article.html". Empty by default.
OG_TITLE_DIVERGENCE_ALLOWLIST = set()

def check_file(filepath, expected_locale, cards=None):
    issues = []
    rel_path = os.path.relpath(filepath, ROOT_DIR)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Compare the values browsers read, including decoded HTML entities. Literal
    # ampersands, &amp; and numeric entities can encode the same metadata value.
    head = BeautifulSoup(content, 'html.parser').head
    title = head.find('title') if head else None

    def metadata(attribute, name):
        tag = head.find('meta', attrs={attribute: re.compile('^' + re.escape(name) + '$', re.I)}) if head else None
        return tag.get('content', '').strip() if tag else None

    title_text = title.get_text().strip() if title else None
    description = metadata('name', 'description')
    og_title = metadata('property', 'og:title')
    og_description = metadata('property', 'og:description')
    og_locale = metadata('property', 'og:locale')
    
    # 1. Check Locale
    if not og_locale:
        issues.append(f"Missing og:locale")
    else:
        found_locale = og_locale
        if found_locale != expected_locale:
            issues.append(f"Invalid og:locale: '{found_locale}'. Expected '{expected_locale}'")

    # 2. Check Title Presence & Parity
    if not og_title:
        issues.append("Missing og:title")
    elif title_text is not None:
        t = title_text
        ot = og_title
        # A shorter social title may omit the page title's branding suffix.
        if t != ot and ot not in t \
                and rel_path.replace(os.sep, '/') not in OG_TITLE_DIVERGENCE_ALLOWLIST:
             issues.append(f"Title vs OG Title mismatch.\n      Title: {t}\n      OG:    {ot}")

    # 3. Check Description Presence & Parity
    if not og_description:
        issues.append("Missing og:description")
    elif description is not None:
        d = description
        od = og_description
        if d != od:
             issues.append(f"Description vs OG Description mismatch.\n      Meta: {d[:50]}...\n      OG:   {od[:50]}...")

    if cards is not None:
        og_image = metadata('property', 'og:image')
        twitter_image = metadata('name', 'twitter:image')
        try:
            cards.verify_card(og_image)
        except GenerationError as error:
            issues.append(str(error))
        if twitter_image != og_image or not twitter_image:
            issues.append('Twitter image must match the verified Open Graph image')
    return issues

def audit_og_tags():
    print("## Open Graph Audit")
    print(f"{'File':<40} | {'Issues'}")
    print("-" * 100)
    
    total_issues = 0
    
    try:
        with CardBuild(ROOT_DIR) as cards:
            for path in indexable_pages():
                file_issues = check_file(path, 'it_IT' if path.startswith('it/') else 'en_US', cards)
                if file_issues:
                    print(f"{path:<40} | Found {len(file_issues)} issues:")
                    for issue in file_issues:
                        print(f"  - {issue}")
                    total_issues += len(file_issues)
    except (GenerationError, OSError) as error:
        print(f'Social image verification failed: {error}')
        return 1

    if total_issues == 0:
        print("\n✅ All Open Graph tags are consistent and valid.")
    else:
        print(f"\n⚠️ Found {total_issues} total OG issues.")
    return 1 if total_issues else 0

if __name__ == "__main__":
    sys.exit(audit_og_tags())
