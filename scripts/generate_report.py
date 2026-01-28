import sys
import os
import datetime
import io
from contextlib import redirect_stdout

# Import sibling scripts by adding current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# These imports must match actual file names in scripts/
import audit_seo
import audit_links_advanced # Replaces broken_link_checker
import audit_schema
import audit_headings
import advanced_image_check # match file name
# import audit_assets # Optional, overlaps with links_advanced

# Define output path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(ROOT_DIR, "System")
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)
OUTPUT_FILE = os.path.join(REPORT_DIR, "SEO_Audit_Report.md")

def capture_output(func):
    f = io.StringIO()
    with redirect_stdout(f):
        try:
            func()
        except SystemExit:
            pass # scripts might call sys.exit
        except Exception as e:
            print(f"Error running audit: {e}")
    return f.getvalue()

def main():
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# Milano Sensual Congress - SEO Audit Report\n")
            f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Location:** `System/SEO_Audit_Report.md`\n\n")
            
            print("Running SEO Audit...")
            f.write("## 1. SEO Metadata Audit\n")
            f.write("Checking Titles, Meta Descriptions, and Keywords...\n")
            f.write("```text\n")
            f.write(capture_output(lambda: audit_seo.audit_seo(ROOT_DIR)))
            f.write("```\n\n")
            
            print("Running Link Audit...")
            f.write("## 2. Broken Internal Links\n")
            f.write("Validating all internal hrefs...\n")
            f.write("```text\n")
            f.write(capture_output(audit_links_advanced.check_broken_links))
            f.write("```\n\n")
            
            print("Running Heading Audit...")
            f.write("## 3. Heading Structure\n")
            f.write("Validating H1-H6 hierarchy order...\n")
            f.write("```text\n")
            f.write(capture_output(lambda: audit_headings.check_files("."))) # adapts call format
            f.write("```\n\n")
            
            print("Running Image Quality Audit...")
            f.write("## 4. Advanced Image Quality Audit\n")
            f.write("Checking for Image Count, Alt Text, and Responsive Attributes...\n")
            f.write("```text\n")
            f.write(capture_output(advanced_image_check.check_advanced_image_quality))
            f.write("```\n\n")
            
            print("Running Schema Audit...")
            f.write("## 5. Schema Audit\n")
            f.write("Validating JSON-LD structure...\n")
            f.write("```text\n")
            f.write(capture_output(audit_schema.audit_schema))
            f.write("```\n\n")
            
    except Exception as e:
        print(f"Error generating report: {e}")
        return

    print(f"Report successfully generated at: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
