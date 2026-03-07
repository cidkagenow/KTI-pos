"""Import all data from CSV exports into the database.

Usage:
    python seeds/import_all.py          # Import (skip tables with data)
    python seeds/import_all.py --reset  # Truncate all tables first, then import
"""
import sys
import os
import csv
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal

SEEDS_DIR = Path(__file__).parent

# Order matters: respect foreign key dependencies
TABLES = [
    "brands",
    "categories",
    "warehouses",
    "clients",
    "suppliers",
    "document_series",
    "products",
    "inventory",
]

RESET_MODE = "--reset" in sys.argv

db = SessionLocal()

if RESET_MODE:
    print("=== RESET MODE: truncating all tables ===")
    # Truncate in reverse order (respect FK dependencies)
    for table in reversed(TABLES):
        try:
            db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            print(f"  TRUNCATED {table}")
        except Exception as e:
            db.rollback()
            print(f"  WARN truncate {table}: {e}")
    db.commit()
    print()

for table in TABLES:
    csv_path = SEEDS_DIR / f"{table}.csv"
    if not csv_path.exists():
        print(f"SKIP {table}: no CSV file")
        continue

    # Check if table already has data
    count = db.execute(text(f"SELECT count(*) FROM {table}")).scalar()
    if count > 0:
        print(f"SKIP {table}: already has {count} rows")
        continue

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows = list(reader)

    if not rows:
        print(f"SKIP {table}: empty CSV")
        continue

    # Build INSERT statement
    col_list = ", ".join(columns)
    param_list = ", ".join([f":{c}" for c in columns])
    sql = text(f"INSERT INTO {table} ({col_list}) VALUES ({param_list})")

    # Clean up empty strings to None
    clean_rows = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            clean[k] = None if v == "" else v
        clean_rows.append(clean)

    try:
        db.execute(sql, clean_rows)

        # Reset sequence to max id
        if "id" in columns:
            db.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
            ))

        db.commit()
        print(f"OK {table}: {len(rows)} rows imported")
    except Exception as e:
        db.rollback()
        print(f"ERROR {table}: {e}")

print("\nListo! All data imported.")
