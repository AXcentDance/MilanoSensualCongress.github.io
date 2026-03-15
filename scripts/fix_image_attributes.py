import os
import re

def fix_image_attributes():
    updated_files = 0
    for root, dirs, files in os.walk('/Users/slamitza/MilanoSensualCongress'):
        if '.git' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                def add_attributes(match):
                    img_tag = match.group(0)
                    modified = False
                    
                    if 'loading=' not in img_tag and 'hero' not in img_tag.lower():
                        img_tag = img_tag.replace('<img ', '<img loading="lazy" ')
                        modified = True
                        
                    if 'width=' not in img_tag:
                        img_tag = img_tag.replace('<img ', '<img width="800" ')
                        modified = True
                        
                    if 'height=' not in img_tag:
                        img_tag = img_tag.replace('<img ', '<img height="600" ')
                        modified = True
                        
                    return img_tag

                new_content = re.sub(r'<img\s+[^>]*>', add_attributes, content)
                
                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated: {filepath}")
                    updated_files += 1

    print(f"Complete! Updated {updated_files} files with missing image attributes.")

if __name__ == "__main__":
    fix_image_attributes()
