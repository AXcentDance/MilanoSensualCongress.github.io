import os
import re
# Check if bs4 is available, if not, handle gracefully or use regex fallback?
# User snippet imports bs4. I will assume it is available or I should check.
# If not available, I'll attempt a regex extraction for body text.
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    import html

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(ROOT_DIR, 'llms-full.txt')

IGNORE_PATTERNS = [
    'node_modules', '.git', 'tmp', '.gemini', '__pycache__', 'scripts',
    'google', 'assets'
]

PRIORITY = [
    'index.html',
    'schedule.html',
    'registration.html',
    'cart.html',
    'events.html',
    'about.html',
    'contact.html'
]

def should_ignore(path):
    for pattern in IGNORE_PATTERNS:
        if pattern in path.split(os.sep):
            return True
    return False

def get_file_priority(filename):
    for i, p in enumerate(PRIORITY):
        if filename == p:
            return i
    if 'blog-posts' in filename:
        return 100
    if 'de/' in filename or 'it/' in filename:
        return 50
    return 10

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def process_file_regex(file_path):
    # Fallback if bs4 is missing
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple regex extractions
    title_m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.S)
    title = html.unescape(title_m.group(1).strip()) if title_m else "No Title"
    
    desc_m = re.search(r'<meta name="description"\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
    description = html.unescape(desc_m.group(1).strip()) if desc_m else ""
    
    # Remove script/style
    clean = re.sub(r'<(script|style|noscript|iframe|svg)[^>]*>.*?</\1>', '', content, flags=re.IGNORECASE | re.S)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', clean)
    text = html.unescape(text)
    
    rel_path = os.path.relpath(file_path, ROOT_DIR)
    
    return {
        'path': rel_path,
        'title': title,
        'description': description,
        'content': clean_text(text)
    }

def process_file(file_path):
    if not HAS_BS4:
        return process_file_regex(file_path)
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
        
        meta_desc = ""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            meta_desc = meta['content'].strip()
            
        for script in soup(["script", "style", "noscript", "iframe", "svg"]):
            script.extract()
            
        text = soup.get_text(separator=' ')
        return {
            'path': os.path.relpath(file_path, ROOT_DIR),
            'title': title,
            'description': meta_desc,
            'content': clean_text(text)
        }
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    print(f"Scanning {ROOT_DIR} for HTML files...")
    
    html_files = []
    for root, dirs, files in os.walk(ROOT_DIR):
        if should_ignore(root):
            continue
        for file in files:
            if file.endswith('.html'):
                full_path = os.path.join(root, file)
                if not should_ignore(full_path):
                    html_files.append(full_path)
    
    html_files.sort(key=lambda p: (get_file_priority(os.path.relpath(p, ROOT_DIR)), os.path.relpath(p, ROOT_DIR)))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        out.write(f"# Website Content Dump\n# Generated automatically. Pages: {len(html_files)}\n\n---\n\n")
        
        for file_path in html_files:
            data = process_file(file_path)
            if data:
                print(f"Writing {data['path']}...")
                out.write(f"# Page: {data['title']} ({data['path']})\n")
                if data['description']:
                    out.write(f"Description: {data['description']}\n")
                out.write("\n")
                out.write(data['content'])
                out.write("\n\n---\n\n")
                
    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
