"""Report the same public-page indexing decisions used by the generators."""
from generation_support import run_generator
from site_files import page_manifest

def main():
    pages = page_manifest()
    print(f"{'File':<50} | Indexing status")
    print("-" * 80)
    
    for page in pages:
        status = 'Indexable' if page['indexable'] else 'Approved noindex utility'
        print(f"{page['file']:<50} | {status}")

if __name__ == "__main__":
    raise SystemExit(run_generator(main))
