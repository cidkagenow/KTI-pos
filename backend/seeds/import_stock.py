"""Import products from KTI2 StockReport.csv into the new database."""
import csv
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, "/Users/cidkagenow/kti-pos/backend")

from app.database import SessionLocal
from app.models.product import Product, Brand, Category
from app.models.inventory import Inventory

CSV_PATH = "/Users/cidkagenow/Desktop/KTI/StockReport.csv"

# Column indices in the CSV (each row has repeated header + data)
COL_CATEGORY = 25  # LINEA value (e.g. ARTICULOS, PERNOS, RETENES)
COL_NAME = 26      # DESCRIPCION
COL_BRAND = 27     # MARCA
COL_COST = 28      # COSTO S/
COL_STOCK = 29     # ST. DISP.


def parse_decimal(val: str) -> Decimal:
    """Parse a decimal value, handling commas and empty strings."""
    val = val.strip().replace(",", "")
    if not val:
        return Decimal("0")
    try:
        return Decimal(val)
    except InvalidOperation:
        return Decimal("0")


def main():
    db = SessionLocal()
    try:
        # Get warehouse ID 1 (ALMACEN PRINCIPAL)
        warehouse_id = 1

        # Cache for brands and categories
        brand_cache: dict[str, int] = {}
        category_cache: dict[str, int] = {}

        # Load existing brands/categories from seed
        for b in db.query(Brand).filter(Brand.is_active == True).all():
            brand_cache[b.name.upper().strip()] = b.id
        for c in db.query(Category).filter(Category.is_active == True).all():
            category_cache[c.name.upper().strip()] = c.id

        products_added = 0
        brands_created = 0
        categories_created = 0
        skipped = 0
        seen_names: set[str] = set()

        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, 1):
                if len(row) < 30:
                    skipped += 1
                    continue

                category_name = row[COL_CATEGORY].strip()
                product_name = row[COL_NAME].strip()
                brand_name = row[COL_BRAND].strip()
                cost_str = row[COL_COST].strip()
                stock_str = row[COL_STOCK].strip()

                # Skip empty product names or header-like rows
                if not product_name or product_name == "DESCRIPCION":
                    skipped += 1
                    continue

                # Skip duplicates (same name)
                name_key = product_name.upper()
                if name_key in seen_names:
                    skipped += 1
                    continue
                seen_names.add(name_key)

                # Parse cost and stock
                cost_price = parse_decimal(cost_str)
                stock_qty = parse_decimal(stock_str)
                # Treat negative stock as 0
                if stock_qty < 0:
                    stock_qty = Decimal("0")

                # Get or create brand
                brand_id = None
                if brand_name:
                    brand_key = brand_name.upper().strip()
                    if brand_key not in brand_cache:
                        new_brand = Brand(name=brand_name.strip(), is_active=True)
                        db.add(new_brand)
                        db.flush()
                        brand_cache[brand_key] = new_brand.id
                        brands_created += 1
                    brand_id = brand_cache[brand_key]

                # Get or create category
                category_id = None
                if category_name:
                    cat_key = category_name.upper().strip()
                    if cat_key not in category_cache:
                        new_cat = Category(name=category_name.strip(), is_active=True)
                        db.add(new_cat)
                        db.flush()
                        category_cache[cat_key] = new_cat.id
                        categories_created += 1
                    category_id = category_cache[cat_key]

                # Generate product code (sequential)
                code = str(products_added + 1).zfill(5)

                product = Product(
                    code=code,
                    name=product_name,
                    brand_id=brand_id,
                    category_id=category_id,
                    cost_price=cost_price,
                    unit_price=Decimal("0"),  # No sale price in CSV
                    is_active=True,
                )
                db.add(product)
                db.flush()

                # Create inventory record if stock > 0
                if stock_qty > 0:
                    inv = Inventory(
                        product_id=product.id,
                        warehouse_id=warehouse_id,
                        quantity=int(stock_qty),
                    )
                    db.add(inv)

                products_added += 1
                if products_added % 1000 == 0:
                    print(f"  ...{products_added} products processed")

        db.commit()
        print(f"\nImport complete!")
        print(f"  Products added: {products_added}")
        print(f"  Brands created: {brands_created}")
        print(f"  Categories created: {categories_created}")
        print(f"  Rows skipped (duplicates/empty): {skipped}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
