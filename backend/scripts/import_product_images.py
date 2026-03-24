#!/usr/bin/env python3
"""
Bulk import product images by matching filenames to product names.

Usage (from inside Docker backend container):
    python /app/scripts/import_product_images.py /path/to/images

Or from host:
    docker compose exec backend python scripts/import_product_images.py /app/uploads/products

The script:
1. Reads all product names from DB
2. Normalizes names (replace /  " : * with _)
3. Matches against image filenames (without extension)
4. Copies matched images to /app/uploads/products/ (renamed to {product_id}.{ext})
5. Updates product.image_path in the database
"""
import os
import re
import shutil
import sys

# Add parent dir so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.product import Product

UPLOAD_DIR = "/app/uploads/products"


def normalize(name: str) -> str:
    """Normalize a product name to match filename conventions."""
    n = name.replace("/", "_").replace('"', "_").replace(":", "_").replace("*", "_")
    n = re.sub(r"\s+", " ", n).strip()
    return n.upper()


def main():
    source_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not source_dir:
        print("Usage: python import_product_images.py <source_images_dir>")
        sys.exit(1)

    if not os.path.isdir(source_dir):
        print(f"Error: {source_dir} is not a directory")
        sys.exit(1)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Build map: normalized filename -> actual filename
    print("Scanning image files...")
    file_map: dict[str, str] = {}
    for f in os.listdir(source_dir):
        base, ext = os.path.splitext(f)
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        key = normalize(base)
        file_map[key] = f
    print(f"  Found {len(file_map)} image files")

    # Load products
    db = SessionLocal()
    products = db.query(Product).filter(Product.is_active == True).all()
    print(f"  Found {len(products)} active products")

    matched = 0
    skipped = 0
    unmatched = 0
    unmatched_names = []

    for p in products:
        key = normalize(p.name)
        if key not in file_map:
            unmatched += 1
            if unmatched <= 20:
                unmatched_names.append(f"  {p.id}: {p.name}")
            continue

        src_file = file_map[key]
        ext = os.path.splitext(src_file)[1].lower()
        dest_name = f"{p.id}{ext}"
        dest_path = os.path.join(UPLOAD_DIR, dest_name)

        # Skip if already exists and image_path is set
        if p.image_path == dest_name and os.path.exists(dest_path):
            skipped += 1
            continue

        # Copy image
        src_path = os.path.join(source_dir, src_file)
        if source_dir != UPLOAD_DIR:
            shutil.copy2(src_path, dest_path)

        # Update DB
        p.image_path = dest_name
        matched += 1

        if matched % 1000 == 0:
            db.commit()
            print(f"  Processed {matched} images...")

    db.commit()
    db.close()

    print(f"\nResults:")
    print(f"  Matched & imported: {matched}")
    print(f"  Already up-to-date: {skipped}")
    print(f"  Unmatched: {unmatched}")
    if unmatched_names:
        print(f"\nSample unmatched products:")
        for name in unmatched_names:
            print(name)


if __name__ == "__main__":
    main()
