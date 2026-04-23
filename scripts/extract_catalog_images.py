"""
Extract product images from supplier PDF catalogs and match to KTI-POS products.

Usage:
    python3 scripts/extract_catalog_images.py

Processes two catalog PDFs:
1. GDM (Grupo Delta Motors) - Lista Distribuidor
2. Lima catalog - LISTA_PRECIO

For each catalog entry:
- Extracts product image
- Extracts product name
- Fuzzy matches against all products in the database
- Saves matching images to backend/uploads/products/
"""

import csv
import os
import re
import sys
from io import BytesIO
from pathlib import Path

import fitz  # pymupdf
from thefuzz import fuzz
from PIL import Image

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "backend" / "uploads" / "products"
PRODUCTS_CSV = "/tmp/kti_products.csv"
OUTPUT_DIR = BASE_DIR / "scripts" / "catalog_extracted"

# Catalog PDFs
CATALOGS = [
    {
        "name": "GDM",
        "path": "/Users/cidkagenow/Library/Containers/net.whatsapp.WhatsApp/Data/tmp/documents/A5E401F6-7418-4500-BFA8-8673CC45183B/Lista Distribuidor.pdf",
        "skip_pages": [0],  # Cover page
        "name_extractor": "gdm",
    },
    {
        "name": "Lima",
        "path": "/Users/cidkagenow/Library/Containers/net.whatsapp.WhatsApp/Data/tmp/documents/7150A531-B7AF-474F-A899-D25B214F2798/LISTA_PRECIO_30-03-2026.pdf",
        "skip_pages": [0],  # Cover page
        "name_extractor": "lima",
    },
]

MIN_MATCH_SCORE = 75  # Minimum fuzzy match score (0-100)
MIN_IMAGE_SIZE = 500  # Minimum image bytes to avoid tiny icons


def load_products():
    """Load products from CSV export."""
    products = []
    with open(PRODUCTS_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                "id": int(row["id"]),
                "code": row["code"],
                "name": row["name"].strip(),
                "image_path": row["image_path"].strip() if row["image_path"] else "",
                "name_normalized": normalize(row["name"]),
            })
    return products


def normalize(text):
    """Normalize product name for matching."""
    text = text.upper().strip()
    # Remove common suffixes/prefixes that differ between catalog and DB
    text = re.sub(r'\s*-\s*$', '', text)
    text = re.sub(r'\s+', ' ', text)
    # Remove brand suffixes that might not match
    for brand in ["GDM", "HAIOSKY", "QIAOGUAN", "BJR", "KIGCOL", "RALCO", "TAJAL"]:
        text = re.sub(rf'\s*-?\s*{brand}\s*$', '', text)
    return text


def extract_gdm_entries(doc, page_idx):
    """Extract product entries from a GDM catalog page."""
    page = doc[page_idx]
    blocks = page.get_text("dict")["blocks"]

    # Get product images (left side, x < 200)
    img_blocks = []
    for b in blocks:
        if b.get("type") == 1:
            bbox = b["bbox"]
            if bbox[0] < 200:  # Left side = product image
                img_blocks.append(b)

    # Get product names (bold text, not header)
    names = []
    for b in blocks:
        if "lines" not in b:
            continue
        for line in b["lines"]:
            text = "".join([span["text"] for span in line["spans"]]).strip()
            if not text:
                continue
            is_bold = any(span["flags"] & 2**4 for span in line["spans"])
            if is_bold and text != "LISTA DE PRECIOS - GRUPO DELTA MOTORS SAC":
                y = line["bbox"][1]
                # Skip if it looks like a field label
                if any(text.startswith(x) for x in ["Codigo", "U.M.", "Procedencia", "Precio", "Cant x caja"]):
                    continue
                names.append({"text": text, "y": y})

    # Match images to names by y proximity
    entries = []
    for name_item in names:
        # Find closest image above or near the name
        best_img = None
        best_dist = 999
        for img_b in img_blocks:
            img_y = img_b["bbox"][1]
            dist = abs(name_item["y"] - img_y)
            if dist < best_dist and dist < 30:
                best_dist = dist
                best_img = img_b

        if best_img:
            entries.append({
                "name": name_item["text"],
                "image_block": best_img,
            })

    return entries


def extract_lima_entries(doc, page_idx):
    """Extract product entries from a Lima catalog page."""
    page = doc[page_idx]
    blocks = page.get_text("dict")["blocks"]

    # Get product images (left side)
    img_blocks = []
    for b in blocks:
        if b.get("type") == 1:
            bbox = b["bbox"]
            if bbox[0] < 200:
                img_blocks.append(b)

    # Get product names (white text in colored headers, size ~8.2)
    names = []
    for b in blocks:
        if "lines" not in b:
            continue
        for line in b["lines"]:
            spans = line["spans"]
            text = "".join([s["text"] for s in spans]).strip()
            if not text:
                continue
            # White text (color=16777215) = header bar product names
            is_white = any(s.get("color", 0) == 16777215 for s in spans)
            is_bold = any(s["flags"] & 2**4 for s in spans)
            if is_white and is_bold and text != "LISTA DE PRECIOS - LIMA":
                y = line["bbox"][1]
                names.append({"text": text, "y": y})

    entries = []
    for name_item in names:
        best_img = None
        best_dist = 999
        for img_b in img_blocks:
            img_y = img_b["bbox"][1]
            dist = abs(name_item["y"] - img_y)
            if dist < best_dist and dist < 50:
                best_dist = dist
                best_img = img_b

        if best_img:
            entries.append({
                "name": name_item["text"],
                "image_block": best_img,
            })

    return entries


def save_image_from_block(doc, page_idx, img_block, output_path):
    """Extract and save an image from a page image block."""
    page = doc[page_idx]

    # Get the image from the block
    # img_block has image data embedded
    if "image" in img_block:
        img_data = img_block["image"]
    else:
        # Try extracting via xref
        bbox = fitz.Rect(img_block["bbox"])
        pix = page.get_pixmap(clip=bbox, dpi=150)
        img_data = pix.tobytes("png")

    if len(img_data) < MIN_IMAGE_SIZE:
        return False

    try:
        img = Image.open(BytesIO(img_data))
        # Convert to RGB if needed
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        # Save as JPEG
        img.save(output_path, "JPEG", quality=85)
        return True
    except Exception:
        # Fallback: save raw bytes
        try:
            with open(output_path, "wb") as f:
                f.write(img_data)
            return True
        except Exception:
            return False


def find_best_match(catalog_name, products):
    """Find the best matching product for a catalog entry name."""
    catalog_normalized = normalize(catalog_name)

    best_score = 0
    best_product = None

    for p in products:
        # Try multiple matching strategies
        score1 = fuzz.token_sort_ratio(catalog_normalized, p["name_normalized"])
        score2 = fuzz.partial_ratio(catalog_normalized, p["name_normalized"])
        score = max(score1, score2)

        if score > best_score:
            best_score = score
            best_product = p

    if best_score >= MIN_MATCH_SCORE:
        return best_product, best_score
    return None, best_score


def main():
    print("Loading products from database...")
    products = load_products()
    print(f"  {len(products)} products loaded")

    no_image = [p for p in products if not p["image_path"]]
    print(f"  {len(no_image)} products without images")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    matches = []
    no_match = []

    for catalog in CATALOGS:
        print(f"\nProcessing {catalog['name']} catalog: {catalog['path']}")

        if not os.path.exists(catalog["path"]):
            print(f"  SKIP: File not found")
            continue

        doc = fitz.open(catalog["path"])
        total_pages = doc.page_count
        print(f"  {total_pages} pages")

        extractor = extract_gdm_entries if catalog["name_extractor"] == "gdm" else extract_lima_entries

        catalog_entries = 0
        catalog_matches = 0

        for page_idx in range(total_pages):
            if page_idx in catalog.get("skip_pages", []):
                continue

            try:
                entries = extractor(doc, page_idx)
            except Exception as e:
                continue

            for entry in entries:
                catalog_entries += 1
                product, score = find_best_match(entry["name"], products)

                if product:
                    # Only save if product has no image yet
                    if not product["image_path"]:
                        img_filename = f"{product['code']}.jpg"
                        img_path = UPLOADS_DIR / img_filename

                        saved = save_image_from_block(doc, page_idx, entry["image_block"], str(img_path))

                        if saved:
                            catalog_matches += 1
                            matches.append({
                                "product_id": product["id"],
                                "product_code": product["code"],
                                "product_name": product["name"],
                                "catalog_name": entry["name"],
                                "score": score,
                                "image_file": img_filename,
                                "catalog": catalog["name"],
                            })
                            # Mark as having image now (prevent duplicate matches)
                            product["image_path"] = img_filename
                else:
                    no_match.append({
                        "catalog_name": entry["name"],
                        "catalog": catalog["name"],
                    })

            if (page_idx + 1) % 50 == 0:
                print(f"  Page {page_idx + 1}/{total_pages} — {catalog_entries} entries, {catalog_matches} matches")

        print(f"  Done: {catalog_entries} entries, {catalog_matches} new image matches")
        doc.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Total matches (new images): {len(matches)}")
    print(f"  Unmatched catalog entries: {len(no_match)}")

    # Generate SQL to update image_path in database
    if matches:
        sql_path = OUTPUT_DIR / "update_images.sql"
        with open(sql_path, "w") as f:
            for m in matches:
                f.write(f"UPDATE products SET image_path = 'products/{m['image_file']}' WHERE id = {m['product_id']};\n")
        print(f"\n  SQL file: {sql_path}")
        print(f"  Run: docker compose exec -T db psql -U ktipos -d ktipos < scripts/catalog_extracted/update_images.sql")

    # Save match report
    report_path = OUTPUT_DIR / "match_report.csv"
    with open(report_path, "w") as f:
        f.write("product_id,product_code,product_name,catalog_name,score,catalog\n")
        for m in matches:
            f.write(f"{m['product_id']},{m['product_code']},\"{m['product_name']}\",\"{m['catalog_name']}\",{m['score']},{m['catalog']}\n")
    print(f"  Report: {report_path}")

    # Show matches
    if matches:
        print(f"\nMatched products:")
        for m in matches:
            print(f"  [{m['score']}%] {m['product_name']}")
            print(f"       ← {m['catalog_name']} ({m['catalog']})")


if __name__ == "__main__":
    main()
