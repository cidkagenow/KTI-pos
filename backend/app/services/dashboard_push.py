"""
Push dashboard stats to the remote KTI Dashboard.

Runs every 60 seconds via APScheduler. Sends sales summary + low stock
to the dashboard's /api/ingest endpoint, authenticated by API key.
"""

import logging
from datetime import date, timedelta

import httpx
from sqlalchemy import func, case

from app.config import settings
from app.database import SessionLocal
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.sale import Sale
from app.models.warehouse import Warehouse

logger = logging.getLogger(__name__)

# Match the timezone logic from reports.py
_lima = func.timezone("America/Lima", Sale.created_at)
SALE_STATUSES = ("FACTURADO",)


def _count_and_total(db, from_date: date) -> tuple[int, float]:
    result = (
        db.query(
            func.count(case((Sale.doc_type != "NOTA_CREDITO", Sale.id))),
            func.coalesce(
                func.sum(
                    case((Sale.doc_type == "NOTA_CREDITO", -Sale.total), else_=Sale.total)
                ),
                0,
            ),
        )
        .filter(
            Sale.status.in_(SALE_STATUSES),
            Sale.doc_type != "PROFORMA",
            func.date(_lima) >= from_date,
        )
        .first()
    )
    return int(result[0]), float(result[1])


def push_dashboard_stats():
    """Collect stats and push to dashboard."""
    url = settings.DASHBOARD_URL
    api_key = settings.DASHBOARD_API_KEY

    if not url or not api_key:
        return  # Not configured, skip silently

    db = SessionLocal()
    try:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        today_sales, today_total = _count_and_total(db, today)
        week_sales, week_total = _count_and_total(db, start_of_week)
        month_sales, month_total = _count_and_total(db, start_of_month)

        low_stock_count = (
            db.query(func.count(Inventory.id))
            .join(Product, Inventory.product_id == Product.id)
            .filter(Inventory.quantity <= Product.min_stock)
            .scalar()
        ) or 0

        # Get actual low stock items (top 20)
        low_stock_rows = (
            db.query(Inventory, Product, Warehouse)
            .join(Product, Inventory.product_id == Product.id)
            .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
            .filter(Inventory.quantity <= Product.min_stock)
            .order_by(Inventory.quantity.asc())
            .limit(20)
            .all()
        )

        low_stock_items = [
            {
                "product_code": p.code,
                "product_name": p.name,
                "warehouse_name": w.name,
                "quantity": inv.quantity,
            }
            for inv, p, w in low_stock_rows
        ]

        payload = {
            "branch_id": settings.DASHBOARD_BRANCH_ID,
            "today_sales": today_sales,
            "today_total": today_total,
            "week_sales": week_sales,
            "week_total": week_total,
            "month_sales": month_sales,
            "month_total": month_total,
            "low_stock_count": low_stock_count,
            "low_stock_items": low_stock_items,
        }

        resp = httpx.post(
            f"{url}/api/ingest",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )

        if resp.status_code == 200:
            logger.debug("Dashboard push OK: %s", resp.json())
        else:
            logger.warning("Dashboard push failed (%d): %s", resp.status_code, resp.text)

    except Exception:
        logger.exception("Dashboard push error")
    finally:
        db.close()
