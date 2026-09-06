import os
import re
import json
import sys
from urllib.parse import urlsplit
from site_files import site_pages

ROOT_DIR = "."
SITE = "https://milanosensualcongress.com"

# Full ISO-8601 with timezone offset, e.g. 2026-11-20T18:00:00+01:00
FULL_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?([+-]\d{2}:\d{2}|Z)$')
DATE_ONLY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# Fields that must be full ISO-8601 with offset (dateModified may be date-only).
STRICT_DATE_FIELDS = ('datePublished', 'startDate', 'endDate', 'validThrough')


def node_types(node):
    t = node.get('@type')
    if isinstance(t, list):
        return t
    return [t] if t else []


def iter_nodes(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from iter_nodes(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_nodes(v)


def collect_ids(obj, defined, referenced):
    """Defining nodes carry @id plus other keys; a bare {"@id": ...} is a reference."""
    for node in iter_nodes(obj):
        nid = node.get('@id')
        if not isinstance(nid, str):
            continue
        if len(node) == 1:
            referenced.add(nid)
        else:
            defined.add(nid)


def target_file_exists(path):
    """True when a clean-URL path maps to a file in the repo."""
    rel = path.lstrip('/')
    if rel in ('', '.'):
        rel = 'index.html'
    candidates = [rel]
    if rel.endswith('/'):
        candidates = [rel + 'index.html']
    elif not rel.endswith('.html'):
        candidates = [rel + '.html', rel + '/index.html', rel]
    return any(os.path.isfile(os.path.join(ROOT_DIR, c)) for c in candidates)


def is_own_organization(node):
    nid = node.get('@id') or ''
    url = node.get('url') or ''
    name = node.get('name') or ''
    return (nid.startswith(SITE) or url.startswith(SITE)
            or 'Milano Sensual' in name)


def check_id_integrity(rel, defined, referenced, sitewide_defined, issues, warnings):
    for ref in sorted(referenced):
        if not ref.startswith(SITE):
            continue
        if ref in defined:
            continue
        split = urlsplit(ref)
        if split.fragment and split.path in ('', '/'):
            # Site-root entity id (e.g. /#organization): needs a defining node
            # on this page; defined elsewhere on the site is warn-only.
            if ref in sitewide_defined:
                warnings.append(
                    f"[{rel}] @id {ref} referenced but not defined on this page "
                    f"(defined elsewhere on the site)")
            else:
                issues.append(f"[{rel}] @id {ref} referenced but defined nowhere on the site")
        elif not target_file_exists(split.path):
            issues.append(f"[{rel}] @id {ref} points at a missing page ({split.path})")


def check_dates(rel, data, issues, warnings):
    for node in iter_nodes(data):
        types = node_types(node)
        for field in STRICT_DATE_FIELDS:
            value = node.get(field)
            if not isinstance(value, str):
                continue
            if FULL_ISO_RE.match(value):
                continue
            if DATE_ONLY_RE.match(value):
                # Date-only: the site's own DanceEvent must carry offsets;
                # datePublished and secondary nodes (CourseInstance, listed
                # third-party events) are warn-only.
                if field != 'datePublished' and 'DanceEvent' in types:
                    issues.append(
                        f"[{rel}] {field} on DanceEvent is date-only: \"{value}\" "
                        f"(needs timezone offset)")
                else:
                    warnings.append(
                        f"[{rel}] date-only {field} \"{value}\" on "
                        f"{'/'.join(types) or 'untyped node'} (should carry a timezone offset)")
            else:
                issues.append(f"[{rel}] malformed {field}: \"{value}\"")
        dm = node.get('dateModified')
        if isinstance(dm, str) and not (FULL_ISO_RE.match(dm) or DATE_ONLY_RE.match(dm)):
            issues.append(f"[{rel}] malformed dateModified: \"{dm}\"")


def check_forbidden_types(rel, data, issues):
    for node in iter_nodes(data):
        types = node_types(node)
        if 'HowTo' in types:
            issues.append(f"[{rel}] forbidden schema type HowTo")
        if 'Organization' in types and is_own_organization(node) \
                and 'aggregateRating' in node:
            issues.append(
                f"[{rel}] aggregateRating on the site's own Organization "
                f"(self-serving review markup)")


def html_files():
    return [os.path.join(ROOT_DIR, page) for page in site_pages(ROOT_DIR)]


def audit_schema():
    print("## Schema Audit")
    print(f"Verifying JSON-LD schemas in {os.path.abspath(ROOT_DIR)}...")

    issues = []
    warnings = []
    parsed = {}   # filepath -> list of parsed JSON-LD blocks

    for filepath in html_files():
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                             content, re.DOTALL)
        blocks = []
        for json_str in matches:
            try:
                blocks.append(json.loads(json_str))
            except json.JSONDecodeError as e:
                issues.append(f"[{os.path.relpath(filepath, ROOT_DIR)}] Invalid JSON-LD Schema: {e}")
        if blocks:
            parsed[filepath] = blocks

    # site-wide @id definitions (for cross-page entity references)
    sitewide_defined = set()
    per_page_ids = {}
    for filepath, blocks in parsed.items():
        defined, referenced = set(), set()
        for data in blocks:
            collect_ids(data, defined, referenced)
        per_page_ids[filepath] = (defined, referenced)
        sitewide_defined |= defined

    for filepath, blocks in parsed.items():
        rel = os.path.relpath(filepath, ROOT_DIR)
        defined, referenced = per_page_ids[filepath]
        check_id_integrity(rel, defined, referenced, sitewide_defined, issues, warnings)
        for data in blocks:
            check_dates(rel, data, issues, warnings)
            check_forbidden_types(rel, data, issues)

    if warnings:
        print(f"WARNINGS (non-fatal), {len(warnings)} item(s):")
        for w in warnings:
            print(f"  ! {w}")

    if issues:
        print(f"⚠️ Found {len(issues)} Schema issues:")
        for i in issues:
            print(i)
        sys.exit(1)
    else:
        print("✅ JSON-LD Schemas are valid JSON and pass deep checks "
              "(@id integrity, date formats, forbidden types).")

if __name__ == "__main__":
    audit_schema()
