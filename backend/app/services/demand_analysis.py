"""
Demand Analysis — tells you which products to buy more or less of.

Analyzes sales velocity vs current stock levels to classify products:
- HIGH DEMAND: selling fast, frequently running low → buy more
- NORMAL: healthy balance of sales vs stock
- SLOW MOVING: low sales relative to stock → buy less next time
- DEAD STOCK: zero sales in 90 days but has stock → stop buying
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product, Brand, Category
from app.models.purchase import PurchaseOrder, PurchaseOrderItem
from app.models.sale import Sale, SaleItem

logger = logging.getLogger(__name__)

SALE_STATUSES = ("FACTURADO",)


def get_demand_analysis(db: Session, warehouse_id: int | None = None, days: int = 90) -> list[dict]:
    """
    Analyze demand for all active products.

    Returns list of products sorted by demand category and velocity.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all active products with stock
    query = (
        db.query(
            Product.id,
            Product.code,
            Product.name,
            Product.cost_price,
            Product.unit_price,
            Product.min_stock,
            Brand.name.label("brand_name"),
            Category.name.label("category_name"),
            func.coalesce(func.sum(Inventory.quantity), 0).label("total_stock"),
        )
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .outerjoin(Inventory, Product.id == Inventory.product_id)
        .filter(Product.is_active == True)  # noqa: E712
    )

    if warehouse_id is not None:
        query = query.filter(Inventory.warehouse_id == warehouse_id)

    query = query.group_by(
        Product.id, Product.code, Product.name, Product.cost_price,
        Product.unit_price, Product.min_stock, Brand.name, Category.name,
    )

    products = query.all()

    # Get sales quantities per product in the period
    sales_data = (
        db.query(
            SaleItem.product_id,
            func.sum(SaleItem.quantity).label("total_sold"),
            func.sum(SaleItem.line_total).label("total_revenue"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.status.in_(SALE_STATUSES),
            Sale.created_at >= cutoff,
        )
        .group_by(SaleItem.product_id)
        .all()
    )
    sales_map = {row[0]: {"sold": int(row[1]), "revenue": float(row[2])} for row in sales_data}

    # Get last purchase cost per product
    # Subquery: most recent RECEIVED PO item per product
    last_purchase = (
        db.query(
            PurchaseOrderItem.product_id,
            PurchaseOrderItem.unit_cost,
        )
        .join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        .filter(PurchaseOrder.status == "RECEIVED")
        .order_by(desc(PurchaseOrder.received_at))
        .all()
    )
    # Keep only the first (most recent) per product
    purchase_cost_map: dict[int, float] = {}
    for row in last_purchase:
        if row[0] not in purchase_cost_map:
            purchase_cost_map[row[0]] = float(row[1])

    results = []
    for p in products:
        pid = p[0]
        total_stock = int(p[8])
        min_stock = p[5] or 0
        cost_price = float(p[3]) if p[3] else purchase_cost_map.get(pid, 0)
        unit_price = float(p[4]) if p[4] else 0

        sale_info = sales_map.get(pid, {"sold": 0, "revenue": 0})
        total_sold = sale_info["sold"]
        total_revenue = sale_info["revenue"]
        daily_sales = total_sold / days if days > 0 else 0

        # Days of stock remaining
        days_of_stock = total_stock / daily_sales if daily_sales > 0 else (999 if total_stock > 0 else 0)

        # Capital tied up in this product
        stock_value = total_stock * cost_price

        # Classify demand
        if total_sold == 0 and total_stock > 0:
            demand = "dead_stock"
            recommendation = "stop_buying"
        elif total_sold == 0 and total_stock == 0:
            continue  # no sales, no stock — irrelevant
        elif daily_sales > 0 and days_of_stock <= 14:
            demand = "high_demand"
            recommendation = "buy_more"
        elif daily_sales > 0 and days_of_stock <= 45:
            demand = "normal"
            recommendation = "maintain"
        elif daily_sales > 0 and days_of_stock > 90:
            demand = "slow_moving"
            recommendation = "buy_less"
        elif daily_sales > 0 and days_of_stock > 45:
            demand = "slow_moving"
            recommendation = "buy_less"
        else:
            demand = "normal"
            recommendation = "maintain"

        results.append({
            "product_id": pid,
            "product_code": p[1],
            "product_name": p[2],
            "brand_name": p[6],
            "category_name": p[7],
            "total_stock": total_stock,
            "min_stock": min_stock,
            "total_sold": total_sold,
            "daily_sales": round(daily_sales, 2),
            "days_of_stock": round(days_of_stock, 1) if days_of_stock < 999 else None,
            "total_revenue": round(total_revenue, 2),
            "stock_value": round(stock_value, 2),
            "cost_price": round(cost_price, 2),
            "unit_price": round(unit_price, 2),
            "demand": demand,
            "recommendation": recommendation,
        })

    # Sort: high_demand first, then normal, slow, dead
    demand_order = {"high_demand": 0, "normal": 1, "slow_moving": 2, "dead_stock": 3}
    results.sort(key=lambda x: (demand_order.get(x["demand"], 4), -x["daily_sales"]))

    return results


def get_price_optimization(db: Session, warehouse_id: int | None = None, days: int = 90) -> list[dict]:
    """
    Price optimization — identifies products where the price should be adjusted.

    Logic:
    - margin_pct = (unit_price - cost_price) / unit_price * 100
    - Combines margin with demand to suggest price changes:
      - High demand + low margin → raise price (leaving money on the table)
      - High demand + high margin → keep price (sweet spot)
      - Low demand + high margin → lower price (margin too high, scaring buyers)
      - Low demand + low margin → review product (bad all around)
      - Dead stock → discount to clear
    """
    # Reuse demand analysis data
    products = get_demand_analysis(db, warehouse_id, days)

    results = []
    for p in products:
        cost = p["cost_price"]
        price = p["unit_price"]

        if cost <= 0 or price <= 0:
            continue  # can't calculate margin without both prices

        margin = price - cost
        margin_pct = (margin / price) * 100
        daily_sales = p["daily_sales"]

        # Classify
        if p["demand"] == "dead_stock":
            price_action = "discount"
            reason = "Sin ventas en 90 dias — aplicar descuento para liberar capital"
        elif p["demand"] == "high_demand" and margin_pct < 15:
            price_action = "raise_price"
            reason = f"Alta demanda ({daily_sales:.1f}/dia) pero margen bajo ({margin_pct:.0f}%) — subir precio"
        elif p["demand"] == "high_demand" and margin_pct >= 15:
            price_action = "keep"
            reason = f"Alta demanda + buen margen ({margin_pct:.0f}%) — precio optimo"
        elif p["demand"] == "slow_moving" and margin_pct > 40:
            price_action = "lower_price"
            reason = f"Pocas ventas con margen alto ({margin_pct:.0f}%) — bajar precio para vender mas"
        elif p["demand"] == "slow_moving" and margin_pct <= 40:
            price_action = "review"
            reason = f"Pocas ventas y margen bajo ({margin_pct:.0f}%) — evaluar si vale la pena"
        elif margin_pct < 10:
            price_action = "raise_price"
            reason = f"Margen muy bajo ({margin_pct:.0f}%) — subir precio"
        elif margin_pct > 60:
            price_action = "lower_price"
            reason = f"Margen muy alto ({margin_pct:.0f}%) — podria vender mas con precio menor"
        else:
            price_action = "keep"
            reason = f"Margen saludable ({margin_pct:.0f}%)"

        results.append({
            "product_id": p["product_id"],
            "product_code": p["product_code"],
            "product_name": p["product_name"],
            "brand_name": p["brand_name"],
            "category_name": p["category_name"],
            "cost_price": cost,
            "unit_price": price,
            "margin": round(margin, 2),
            "margin_pct": round(margin_pct, 1),
            "daily_sales": daily_sales,
            "total_sold": p["total_sold"],
            "total_revenue": p["total_revenue"],
            "total_stock": p["total_stock"],
            "stock_value": p["stock_value"],
            "demand": p["demand"],
            "price_action": price_action,
            "reason": reason,
        })

    # Sort: actionable items first (raise, lower, discount), then keep, then review
    action_order = {"raise_price": 0, "lower_price": 1, "discount": 2, "review": 3, "keep": 4}
    results.sort(key=lambda x: (action_order.get(x["price_action"], 5), -abs(x["margin_pct"] - 25)))

    return results
