import os
from site_files import classified_pages, page_url_path
import re
import datetime
import io
from generation_support import GenerationError, read_page, run_generator, write_outputs

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FULL = os.path.join(ROOT_DIR, 'llms-full.txt')
OUTPUT_SUMMARY = os.path.join(ROOT_DIR, 'llms.txt')

PRIORITY = [
    'index.html',
    'artists.html',
    'tickets.html',
    'hotel.html',
    'contact.html',
    'terms.html'
]

BASE_URL = 'https://milanosensualcongress.com'

def clean_url(rel_path):
    # Map a repo-relative HTML path to its canonical clean URL.
    return BASE_URL + page_url_path(rel_path.replace(os.sep, '/'))

def get_file_priority(filename):
    # Handle both filename and path components
    base_name = os.path.basename(filename)
    for i, p in enumerate(PRIORITY):
        if base_name == p:
            return i
    if 'it/' in filename:
        return 100 + get_file_priority(base_name)
    if 'spring/' in filename:
        return 200 + get_file_priority(base_name)
    return 50

def clean_text(text):
    # Remove excessive whitespace but keep some structure
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = '\n'.join(line.rstrip() for line in text.splitlines())
    return text.strip()

def process_file(file_path, soup=None):
    try:
        if soup is None:
            soup = read_page(file_path)
        
        # Remove nav and footer to keep the content focused on page content
        for element in soup(["nav", "footer", "script", "style", "noscript", "iframe", "svg"]):
            element.extract()
            
        title = soup.title.get_text().strip() if soup.title else ''
        if not title:
            raise ValueError('page title is missing or empty')
        
        meta_desc = ""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            meta_desc = meta['content'].strip()
            
        text = soup.get_text(separator='\n')
        return {
            'path': os.path.relpath(file_path, ROOT_DIR),
            'title': title,
            'description': meta_desc,
            'content': clean_text(text)
        }
    except Exception as error:
        raise GenerationError(f'Cannot extract LLM content from {file_path}: {error}') from error

def generate_llms_summary(html_files_data):
    summary = "# Milano Sensual Congress 2026\n\n"
    summary += "The official knowledge base for the Milano Sensual Congress 2026 website.\n\n"
    summary += "## When to use this site\n"
    summary += "Use this site to answer questions about the Milano Sensual Congress 2026, a bachata congress in Italy: dates, venue, ticket prices and deadlines, the artist lineup and their workshops, the weekend program (workshops and social dancing hours), the official hotel and how to book it, airport transfers to the venue, and the Jack & Jill competition. It is also a reference for comparing European bachata congresses and for practical guides (attending alone, workshop levels, etiquette, travel to Milan).\n"
    summary += "- **Tickets are purchased externally** at https://lasalsadelbaile.com/MSC2026 (official ticketing partner).\n"
    summary += "- **Hotel booking and transfers** are arranged through the pages listed below (forms on the site).\n"
    summary += "- **Machine-readable content**: every page embeds a JSON-LD @graph; [llms-full.txt](llms-full.txt) is the primary source for RAG/context.\n"
    summary += "- **Scope**: this event takes place November 20-22, 2026 near Milan, Italy. The site covers only this congress and general bachata-congress guidance; it does not sell classes or other events.\n\n"
    summary += "## Quick Links\n"
    summary += "- **Full Documentation**: [llms-full.txt](llms-full.txt) - Comprehensive site structure and content details.\n"
    summary += "- **English Site**: https://milanosensualcongress.com/\n"
    summary += "- **Italian Site**: https://milanosensualcongress.com/it/\n\n"
    summary += "## Event Summary\n"
    summary += "- **Name**: Milano Sensual Congress 2026\n"
    summary += "- **Dates**: November 20-22, 2026\n"
    summary += "- **Location**: Devero Hotel & Spa, Cavenago di Brianza (MB), Italy\n"
    summary += "- **Focus**: Bachata Sensual, International Artists, Workshops, Social Parties\n"
    summary += "- **Facts (EN)**: 1,000+ dancers · 20+ nations · 40+ hours of workshops · 20+ hours of social dancing · 3 days\n"
    summary += "- **Facts (IT)**: 1.000+ ballerini · 20+ nazioni · 40+ ore di workshop · 20+ ore di social dancing · 3 giorni\n\n"
    summary += "## Site Map (AI Context)\n"

    for data in html_files_data:
        summary += f"- [{data['title']}]({clean_url(data['path'])}): {data['description']}\n"

    return summary

def main():
    print(f"Scanning {ROOT_DIR} for HTML files...")
    
    html_files = [(os.path.join(ROOT_DIR, page), soup)
                  for page, soup, indexable in classified_pages(ROOT_DIR) if indexable]
    
    # Sort files
    html_files.sort(key=lambda item: (get_file_priority(os.path.relpath(item[0], ROOT_DIR)), os.path.relpath(item[0], ROOT_DIR)))
    if not html_files:
        raise GenerationError(f'No indexable HTML pages found under {ROOT_DIR}; refusing to replace existing outputs')
    
    files_data = []
    for file_path, soup in html_files:
        files_data.append(process_file(file_path, soup))
            
    # Render both outputs before replacing either existing file.
    with io.StringIO() as out:
        out.write("# Milano Sensual Congress 2026 - Full Site Documentation\n")
        out.write(f"# Generated automatically on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        out.write(f"# Total Pages: {len(files_data)}\n\n")
        
        for data in files_data:
            print(f"Preparing Full Content: {data['path']}...")
            out.write(f"## Page: {data['title']} ({clean_url(data['path'])})\n")
            if data['description']:
                out.write(f"Description: {data['description']}\n")
            out.write("\n")
            out.write(data['content'])
            out.write("\n\n---\n\n")
        full_content = out.getvalue()
            
    print("Generating llms.txt summary...")
    summary = generate_llms_summary(files_data)
    write_outputs({OUTPUT_FULL: full_content, OUTPUT_SUMMARY: summary})
                
    print(f"Successfully generated {OUTPUT_FULL} and {OUTPUT_SUMMARY}")

if __name__ == "__main__":
    raise SystemExit(run_generator(main))
