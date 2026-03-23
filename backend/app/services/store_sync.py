"""Client for the standalone store server — sync products and proxy order management."""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.inventory import Inventory
from app.models.product import Brand, Category, Product

logger = logging.getLogger(__name__)

# Track last sync time in memory (resets on server restart → forces full sync)
_last_sync_at: datetime | None = None


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.STORE_API_KEY}"}


def _base_url() -> str:
    return settings.STORE_SERVER_URL.rstrip("/")


def sync_products_to_store(db: Session, force_full: bool = False) -> dict:
    """Push changed products to the store server. Full sync on first call or when forced."""
    global _last_sync_at

    now = datetime.now(timezone.utc)

    # Determine which products to sync
    if _last_sync_at and not force_full:
        # Incremental: only products updated since last sync
        products = (
            db.query(Product)
            .filter(
                Product.is_active == True,
                or_(
                    Product.updated_at >= _last_sync_at,
                    Product.created_at >= _last_sync_at,
                ),
            )
            .all()
        )
        # Also check for stock changes by looking at recent inventory movements
        from app.models.inventory import InventoryMovement
        recently_moved_product_ids = (
            db.query(InventoryMovement.product_id)
            .filter(InventoryMovement.created_at >= _last_sync_at)
            .distinct()
            .all()
        )
        moved_ids = {row[0] for row in recently_moved_product_ids}

        # Add products with stock changes that aren't already in the list
        synced_ids = {p.id for p in products}
        missing_ids = moved_ids - synced_ids
        if missing_ids:
            extra = db.query(Product).filter(Product.id.in_(missing_ids), Product.is_active == True).all()
            products.extend(extra)

        if not products:
            _last_sync_at = now
            return {"synced_brands": 0, "synced_categories": 0, "synced_products": 0, "mode": "incremental (no changes)"}

        sync_mode = "incremental"
    else:
        # Full sync
        products = db.query(Product).filter(Product.is_active == True).all()
        if not products:
            _last_sync_at = now
            return {"synced_brands": 0, "synced_categories": 0, "synced_products": 0, "mode": "full"}
        sync_mode = "full"

    logger.info("Store sync: %s mode, %d products", sync_mode, len(products))

    # Collect referenced brand/category IDs
    brand_ids = {p.brand_id for p in products if p.brand_id is not None}
    category_ids = {p.category_id for p in products if p.category_id is not None}

    brands = db.query(Brand).filter(Brand.id.in_(brand_ids)).all() if brand_ids else []
    categories = db.query(Category).filter(Category.id.in_(category_ids)).all() if category_ids else []

    # Batch stock lookup
    product_ids = [p.id for p in products]
    stock_rows = (
        db.query(
            Inventory.product_id,
            func.coalesce(func.sum(Inventory.quantity), 0).label("total"),
        )
        .filter(Inventory.product_id.in_(product_ids))
        .group_by(Inventory.product_id)
        .all()
    )
    stock_map = {row.product_id: int(row.total) for row in stock_rows}

    payload = {
        "full_sync": sync_mode == "full",
        "brands": [
            {"id": b.id, "name": b.name, "is_active": b.is_active}
            for b in brands
        ],
        "categories": [
            {"id": c.id, "name": c.name, "is_active": c.is_active}
            for c in categories
        ],
        "products": [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "brand_id": p.brand_id,
                "category_id": p.category_id,
                "presentation": p.presentation,
                "unit_price": float(p.unit_price),
                "in_stock": stock_map.get(p.id, 0) > 0,
                "is_online": p.is_online,
            }
            for p in products
        ],
    }

    resp = httpx.post(
        f"{_base_url()}/api/v1/sync/products",
        json=payload,
        headers=_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    _last_sync_at = now

    result = resp.json()
    result["mode"] = sync_mode
    return result


def proxy_store_request(
    method: str,
    path: str,
    json: dict | None = None,
    params: dict | None = None,
) -> httpx.Response:
    """Forward a request to the store server with API key auth."""
    url = f"{_base_url()}{path}"
    resp = httpx.request(
        method=method,
        url=url,
        json=json,
        params=params,
        headers=_headers(),
        timeout=30,
    )
    return resp
