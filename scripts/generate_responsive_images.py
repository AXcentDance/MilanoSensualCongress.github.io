import os
import subprocess

ROOT_DIR = "."
# We want to scan images folder, and spring/images
SEARCH_DIRS = [
    os.path.join(ROOT_DIR, "images"),
    os.path.join(ROOT_DIR, "spring", "images")
]

VARIANTS = [480, 800, 1200]

# Non-content images that never need responsive variants
EXCLUDE_BASENAMES = {"poster", "logo", "qr-code", "milano-sensual-congress-logo-preview"}


def source_width(path):
    """Return the pixel width of an image (0 if it cannot be read)."""
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "stream=width",
            "-of", "csv=p=0", path
        ], stderr=subprocess.DEVNULL)
        return int(out.strip().splitlines()[0])
    except Exception:
        return 0

def generate_variants():
    count = 0
    skipped = 0
    errors = 0

    print("Starting responsive image generation...")
    
    for search_dir in SEARCH_DIRS:
        if not os.path.exists(search_dir):
            continue
            
        print(f"Scanning directory: {search_dir}")

        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if not file.lower().endswith(".webp"):
                    continue
                
                # Skip existing variants so we don't recurse on foo_480w_480w.webp
                if any(f"_{w}w.webp" in file for w in VARIANTS):
                    continue

                src_path = os.path.join(root, file)
                base_name, _ = os.path.splitext(file)

                if base_name in EXCLUDE_BASENAMES:
                    continue

                src_w = source_width(src_path)

                for width in VARIANTS:
                    # Never upscale: skip ladder rungs at or above the source width
                    if src_w and width >= src_w:
                        continue
                    variant_name = f"{base_name}_{width}w.webp"
                    variant_path = os.path.join(root, variant_name)
                    
                    if os.path.exists(variant_path):
                        skipped += 1
                        continue
                    
                    # cwebp -resize width 0 input -o output
                    # 0 height means maintain aspect ratio
                    
                    try:
                        subprocess.check_call([
                            'cwebp', 
                            '-q', '75',
                            '-resize', str(width), '0',
                            src_path, 
                            '-o', variant_path
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print(f"Generated: {variant_name}")
                        count += 1
                    except FileNotFoundError:
                        print("Error: cwebp not found.")
                        return
                    except subprocess.CalledProcessError as e:
                        # Some images might fail if dimension is too small?
                        print(f"Error generating {variant_name}: {e}")
                        errors += 1
    
    print("-" * 50)
    print(f"Generation Complete.")
    print(f"Created: {count}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    generate_variants()
