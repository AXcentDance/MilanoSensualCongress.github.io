import os
from site_files import classified_pages, page_url_path
import re
import io
from generation_support import GenerationError, read_page, run_generator, verify_outputs, write_outputs
from event_facts import date_range, load_current_facts, location_label

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

def generate_llms_summary(html_files_data, facts):
    event = facts['event']
    name = event['name']
    dates = date_range(event)
    location = location_label(event)
    summary = f"# {name}\n\n"
    summary += f"The official knowledge base for the {name} website.\n\n"
    summary += "## When to use this site\n"
    summary += f"Use this site to answer questions about {name}: dates, venue, ticket prices and deadlines, the artist lineup and their workshops, the weekend program (workshops and social dancing hours), the official hotel and how to book it, airport transfers to the venue, and the Jack & Jill competition. It is also a reference for comparing European bachata congresses and for practical guides (attending alone, workshop levels, etiquette, travel to Milan).\n"
    summary += f"- **Tickets are purchased externally** at {facts['ticket_url']} (official ticketing partner).\n"
    summary += "- **Hotel booking and transfers** are arranged through the pages listed below (forms on the site).\n"
    summary += "- **Machine-readable content**: every page embeds a JSON-LD @graph; [llms-full.txt](llms-full.txt) is the primary source for RAG/context.\n"
    summary += f"- **Scope**: this event takes place {dates} at {location}, welcoming dancers from Europe and worldwide. The site covers this congress and general bachata-congress guidance.\n\n"
    summary += "## Quick Links\n"
    summary += "- **Full Documentation**: [llms-full.txt](llms-full.txt) - Comprehensive site structure and content details.\n"
    summary += "- **English Site**: https://milanosensualcongress.com/\n"
    summary += "- **Italian Site**: https://milanosensualcongress.com/it/\n\n"
    summary += "## Event Summary\n"
    summary += f"- **Name**: {name}\n"
    summary += f"- **Dates**: {dates}\n"
    summary += f"- **Location**: {location}\n"
    summary += "- **Focus**: Bachata Sensual, International Artists, Workshops, Social Parties\n"
    summary += f"- **Facts (EN)**: {facts['statistics']['en']}\n"
    summary += f"- **Facts (IT)**: {facts['statistics']['it']}\n\n"
    summary += "## Site Map (AI Context)\n"

    for data in html_files_data:
        summary += f"- [{data['title']}]({clean_url(data['path'])}): {data['description']}\n"

    return summary

def render_outputs():
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

    facts = load_current_facts(ROOT_DIR)
            
    # Render both outputs before replacing either existing file.
    with io.StringIO() as out:
        out.write(f"# {facts['event']['name']} - Full Site Documentation\n")
        out.write("# Generated from the public website; do not edit directly.\n")
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
    summary = generate_llms_summary(files_data, facts)
    return {OUTPUT_FULL: full_content, OUTPUT_SUMMARY: summary}


def main(check=False):
    outputs = render_outputs()
    (verify_outputs if check else write_outputs)(outputs)
                
    print('LLM export freshness verified.' if check else f"Successfully generated {OUTPUT_FULL} and {OUTPUT_SUMMARY}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate complete public LLM exports.')
    parser.add_argument('--check', action='store_true', help='verify freshness without writing')
    args = parser.parse_args()
    raise SystemExit(run_generator(lambda: main(check=args.check)))
