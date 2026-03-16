"""Client for the standalone store server — sync products and proxy order management."""

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.inventory import Inventory
from app.models.product import Brand, Category, Product


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.STORE_API_KEY}"}


def _base_url() -> str:
    return settings.STORE_SERVER_URL.rstrip("/")


def sync_products_to_store(db: Session) -> dict:
    """Push all is_online=true products (with their brands/categories) to the store server."""
    products = (
        db.query(Product)
        .filter(Product.is_active == True, Product.is_online == True)
        .all()
    )

    if not products:
        return {"synced_brands": 0, "synced_categories": 0, "synced_products": 0}

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
            }
            for p in products
        ],
    }

    resp = httpx.post(
        f"{_base_url()}/api/v1/sync/products",
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


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
