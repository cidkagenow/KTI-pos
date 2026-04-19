"""
Smart Restock — suggests what to buy, from which supplier, and how much.

Algorithm:
1. Find products with stock <= min_stock (need restocking)
2. For each product, find the best supplier from purchase order history
   (most recent RECEIVED PO with that product)
3. Calculate suggested quantity based on sales velocity (last 90 days)
4. Group suggestions by supplier with contact info
5. Calculate estimated cost per item and per supplier
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product, Brand
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.sale import Sale, SaleItem
from app.models.warehouse import Warehouse

logger = logging.getLogger(__name__)

SALE_STATUSES = ("FACTURADO", "EMITIDO")


def _get_sales_velocity(db: Session, product_id: int, days: int = 90) -> float:
    """Average units sold per day over the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    total_sold = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            SaleItem.product_id == product_id,
            Sale.status.in_(SALE_STATUSES),
            Sale.created_at >= cutoff,
        )
        .scalar()
    )
    return float(total_sold) / days if days > 0 else 0


def _get_best_supplier(db: Session, product_id: int) -> dict | None:
    """Find the most recent supplier for a product from RECEIVED purchase orders."""
    result = (
        db.query(
            Supplier.id,
            Supplier.business_name,
            Supplier.ruc,
            Supplier.phone,
            Supplier.email,
            Supplier.address,
            Supplier.city,
            PurchaseOrderItem.unit_cost,
            PurchaseOrder.received_at,
        )
        .join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .filter(
            PurchaseOrderItem.product_id == product_id,
            PurchaseOrder.status == "RECEIVED",
        )
        .order_by(desc(PurchaseOrder.received_at))
        .first()
    )

    if not result:
        return None

    return {
        "supplier_id": result[0],
        "business_name": result[1],
        "ruc": result[2],
        "phone": result[3],
        "email": result[4],
        "address": result[5],
        "city": result[6],
        "last_cost": float(result[7]) if result[7] else 0,
        "last_purchase": result[8].isoformat() if result[8] else None,
    }


def get_restock_suggestions(db: Session, warehouse_id: int | None = None) -> list[dict]:
    """
    Generate restock suggestions grouped by supplier.

    Returns a list of supplier groups, each containing:
    - Supplier info (name, ruc, phone, email)
    - List of products to restock (code, name, current stock, suggested qty, cost)
    - Total estimated cost for that supplier
    """

    FORECAST_DAYS = 14  # predict stockouts within 14 days

    # 1. Find active products with min_stock set
    query = (
        db.query(Inventory, Product)
        .join(Product, Inventory.product_id == Product.id)
        .filter(
            Product.is_active == True,  # noqa: E712
            Product.min_stock > 0,
        )
    )

    if warehouse_id is not None:
        query = query.filter(Inventory.warehouse_id == warehouse_id)

    all_items = query.order_by(Product.name).all()

    if not all_items:
        return []

    # 2. For each product, calculate urgency and build suggestions
    supplier_groups: dict[int, dict] = {}
    no_supplier_items: list[dict] = []

    for inv, product in all_items:
        velocity = _get_sales_velocity(db, product.id)

        # Determine urgency
        if inv.quantity <= 0:
            urgency = "critical"  # out of stock
        elif inv.quantity <= product.min_stock:
            urgency = "low"  # below minimum
        elif velocity > 0:
            days_left = inv.quantity / velocity
            if days_left <= FORECAST_DAYS:
                urgency = "upcoming"  # will run out within 14 days
            else:
                continue  # stock is fine, skip
        else:
            continue  # no sales velocity and stock above min, skip

        # Suggested qty: enough for 30 days of sales, minimum = fill to min_stock
        fill_to_min = max(product.min_stock - inv.quantity, 0)
        velocity_based = int(velocity * 30)  # 30 days supply
        suggested_qty = max(fill_to_min, velocity_based, 1)

        supplier_info = _get_best_supplier(db, product.id)

        last_cost = supplier_info["last_cost"] if supplier_info else (float(product.cost_price) if product.cost_price else 0)
        days_until_empty = round(inv.quantity / velocity, 1) if velocity > 0 else None

        item_data = {
            "product_id": product.id,
            "product_code": product.code,
            "product_name": product.name,
            "brand_name": product.brand.name if product.brand else None,
            "current_stock": inv.quantity,
            "min_stock": product.min_stock,
            "suggested_qty": suggested_qty,
            "daily_sales": round(velocity, 2),
            "days_until_empty": days_until_empty,
            "urgency": urgency,
            "last_cost": last_cost,
            "estimated_total": round(suggested_qty * last_cost, 2),
        }

        if not supplier_info:
            no_supplier_items.append(item_data)
            continue

        sid = supplier_info["supplier_id"]
        if sid not in supplier_groups:
            supplier_groups[sid] = {
                "supplier_id": sid,
                "business_name": supplier_info["business_name"],
                "ruc": supplier_info["ruc"],
                "phone": supplier_info["phone"],
                "email": supplier_info["email"],
                "address": supplier_info["address"],
                "city": supplier_info["city"],
                "items": [],
                "total_estimated_cost": 0,
                "total_items": 0,
            }

        supplier_groups[sid]["items"].append(item_data)
        supplier_groups[sid]["total_estimated_cost"] += item_data["estimated_total"]
        supplier_groups[sid]["total_items"] += 1

    # Round totals
    for sg in supplier_groups.values():
        sg["total_estimated_cost"] = round(sg["total_estimated_cost"], 2)

    # Sort: suppliers with more items first
    result = sorted(supplier_groups.values(), key=lambda s: s["total_items"], reverse=True)

    # Add "no supplier" group at the end if any
    if no_supplier_items:
        result.append({
            "supplier_id": None,
            "business_name": "Sin proveedor registrado",
            "ruc": None,
            "phone": None,
            "email": None,
            "address": None,
            "city": None,
            "items": no_supplier_items,
            "total_estimated_cost": round(sum(i["estimated_total"] for i in no_supplier_items), 2),
            "total_items": len(no_supplier_items),
        })

    return result
