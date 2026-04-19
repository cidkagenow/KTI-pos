"""
FX Impact Report — tracks exchange rate impact on dollar-denominated purchases.

Shows:
- Each USD purchase order with the rate used at purchase time
- What it would cost at today's rate
- Gain/loss per PO and total
- Average rate paid vs current rate
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.purchase import PurchaseOrder, Supplier

logger = logging.getLogger(__name__)


def get_fx_impact(db: Session, current_rate: float) -> dict:
    """
    Calculate FX impact for all USD purchase orders.

    Args:
        current_rate: Today's USD/PEN exchange rate

    Returns dict with:
        - orders: list of POs with FX gain/loss
        - summary: total impact, avg rate, etc.
    """
    usd_orders = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.supplier))
        .filter(
            PurchaseOrder.moneda == "DOLARES",
            PurchaseOrder.status == "RECEIVED",
            PurchaseOrder.tipo_cambio.isnot(None),
            PurchaseOrder.total.isnot(None),
        )
        .order_by(PurchaseOrder.received_at.desc())
        .all()
    )

    if not usd_orders:
        return {"orders": [], "summary": None}

    orders = []
    total_usd = 0
    total_paid_soles = 0
    total_at_current = 0

    for po in usd_orders:
        rate_at_purchase = float(po.tipo_cambio)
        total_po = float(po.total)

        # Total in USD (before conversion)
        usd_amount = total_po / rate_at_purchase if rate_at_purchase > 0 else 0

        # What it cost in soles at purchase rate
        paid_soles = total_po  # total is already in soles (converted at purchase time)

        # What it would cost at today's rate
        cost_at_current = usd_amount * current_rate

        # FX impact: negative = you saved money (bought when dollar was cheaper)
        # positive = you lost money (bought when dollar was more expensive)
        fx_impact = paid_soles - cost_at_current

        total_usd += usd_amount
        total_paid_soles += paid_soles
        total_at_current += cost_at_current

        orders.append({
            "po_id": po.id,
            "supplier_name": po.supplier.business_name if po.supplier else "",
            "supplier_ruc": po.supplier.ruc if po.supplier else None,
            "date": po.received_at.strftime("%Y-%m-%d") if po.received_at else po.created_at.strftime("%Y-%m-%d"),
            "usd_amount": round(usd_amount, 2),
            "rate_at_purchase": rate_at_purchase,
            "paid_soles": round(paid_soles, 2),
            "cost_at_current_rate": round(cost_at_current, 2),
            "fx_impact": round(fx_impact, 2),
            "doc_number": po.doc_number or po.supplier_doc or f"OC-{po.id}",
        })

    # Summary
    avg_rate = total_paid_soles / total_usd if total_usd > 0 else 0
    total_fx_impact = total_paid_soles - total_at_current

    summary = {
        "total_orders": len(orders),
        "total_usd": round(total_usd, 2),
        "total_paid_soles": round(total_paid_soles, 2),
        "total_at_current_rate": round(total_at_current, 2),
        "total_fx_impact": round(total_fx_impact, 2),
        "avg_rate_paid": round(avg_rate, 4),
        "current_rate": current_rate,
        "rate_difference": round(current_rate - avg_rate, 4),
    }

    return {"orders": orders, "summary": summary}
