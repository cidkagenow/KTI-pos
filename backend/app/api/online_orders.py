"""Authenticated management API for online orders — proxies to store server."""

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.product import Product
from app.models.sale import DocumentSeries, Sale, SaleItem
from app.models.online_order import OnlineOrder, OnlineOrderItem
from app.schemas.online_order import CancelRequest
from app.api.deps import get_current_user
from app.services.store_sync import proxy_store_request
from app.utils.igv import calc_igv

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_STATUSES = ("PENDIENTE", "CONFIRMADO", "LISTO", "RECOGIDO", "CANCELADO")


def _ensure_store_configured():
    if not settings.STORE_SERVER_URL:
        raise HTTPException(status_code=503, detail="Servidor de tienda no configurado")


def _proxy_response(resp):
    """Convert httpx response to FastAPI response."""
    return JSONResponse(status_code=resp.status_code, content=resp.json())


@router.get("")
def list_online_orders(
    status_filter: str | None = Query(None, alias="status"),
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    params = {}
    if status_filter and status_filter in VALID_STATUSES:
        params["status"] = status_filter
    try:
        resp = proxy_store_request("GET", "/api/v1/orders", params=params)
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.get("/stats")
def order_stats(
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("GET", "/api/v1/orders/stats")
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.get("/{order_id}")
def get_online_order(
    order_id: int,
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("GET", f"/api/v1/orders/{order_id}")
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: int,
    user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request(
            "POST",
            f"/api/v1/orders/{order_id}/confirm",
            json={"staff_name": user.full_name},
        )
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


@router.post("/{order_id}/ready")
def mark_ready(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("POST", f"/api/v1/orders/{order_id}/ready")
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")

    if resp.status_code >= 400:
        return _proxy_response(resp)

    # --- Auto-create BOLETA PREVENTA when order is ready ---
    order_data = resp.json()
    pos_sale_id = None
    try:
        pos_sale_id = _create_sale_from_order(db, order_data, user)
    except Exception:
        logger.exception(
            "Failed to create POS sale for online order %s", order_id
        )

    response_body = order_data
    if pos_sale_id:
        response_body["pos_sale_id"] = pos_sale_id
    return JSONResponse(status_code=resp.status_code, content=response_body)


@router.post("/{order_id}/picked-up")
def mark_picked_up(
    order_id: int,
    _user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request("POST", f"/api/v1/orders/{order_id}/picked-up")
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")


def _create_sale_from_order(db: Session, order_data: dict, user: User) -> int | None:
    """Create a BOLETA PREVENTA sale from a picked-up online order."""
    items_data = order_data.get("items", [])
    if not items_data:
        logger.warning("Online order has no items, skipping sale creation")
        return None

    # Walk-in client
    walk_in = db.query(Client).filter(Client.is_walk_in == True).first()
    if not walk_in:
        logger.error("Walk-in client not found, cannot create sale")
        return None

    # BOLETA series
    doc_series = (
        db.query(DocumentSeries)
        .filter(
            DocumentSeries.doc_type == "BOLETA",
            DocumentSeries.is_active == True,
        )
        .first()
    )
    if not doc_series:
        logger.error("Active BOLETA series not found, cannot create sale")
        return None

    # Build sale items
    sale_items: list[SaleItem] = []
    grand_total = Decimal("0")
    for idx, item in enumerate(items_data):
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        unit_price = Decimal(str(item.get("unit_price", 0)))
        line_total = (Decimal(str(quantity)) * unit_price).quantize(Decimal("0.01"))
        grand_total += line_total

        # Product snapshot
        product = db.query(Product).filter(Product.id == product_id).first()
        sale_items.append(
            SaleItem(
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                discount_pct=Decimal("0"),
                line_total=line_total,
                sort_order=idx,
                product_code=product.code if product else item.get("product_code", ""),
                product_name=product.name if product else item.get("product_name", ""),
                brand_name=(product.brand.name if product and product.brand else item.get("brand_name")),
                presentation=product.presentation if product else item.get("presentation"),
            )
        )

    # IGV
    subtotal, igv_amount, total = calc_igv(grand_total)

    order_code = order_data.get("order_code", "")
    customer_name = order_data.get("customer_name", "")

    sale = Sale(
        doc_type="BOLETA",
        series=doc_series.series,
        doc_number=None,
        client_id=walk_in.id,
        warehouse_id=1,
        seller_id=user.id,
        created_by=user.id,
        payment_cond="CONTADO",
        payment_method="EN_TIENDA",
        subtotal=subtotal,
        igv_amount=igv_amount,
        total=total,
        status="PREVENTA",
        notes=f"Pedido Web #{order_code} - {customer_name}",
        issue_date=date.today(),
        items=sale_items,
    )
    db.add(sale)
    db.flush()

    # Save local OnlineOrder record linked to this sale
    local_order = OnlineOrder(
        order_code=order_code,
        customer_name=customer_name,
        customer_phone=order_data.get("customer_phone", ""),
        customer_email=order_data.get("customer_email"),
        payment_method=order_data.get("payment_method", "EN_TIENDA"),
        payment_reference=order_data.get("payment_reference"),
        subtotal=subtotal,
        igv_amount=igv_amount,
        total=total,
        status="RECOGIDO",
        sale_id=sale.id,
    )
    # Order items for local record
    for item in items_data:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        unit_price = Decimal(str(item.get("unit_price", 0)))
        line_total = (Decimal(str(quantity)) * unit_price).quantize(Decimal("0.01"))
        product = db.query(Product).filter(Product.id == product_id).first()
        local_order.items.append(
            OnlineOrderItem(
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
                product_code=product.code if product else item.get("product_code", ""),
                product_name=product.name if product else item.get("product_name", ""),
                brand_name=(product.brand.name if product and product.brand else item.get("brand_name")),
                presentation=product.presentation if product else item.get("presentation"),
            )
        )
    db.add(local_order)
    db.commit()
    db.refresh(sale)

    logger.info(
        "Created BOLETA PREVENTA sale #%d for online order %s",
        sale.id, order_code,
    )
    return sale.id


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    body: CancelRequest,
    user: User = Depends(get_current_user),
):
    _ensure_store_configured()
    try:
        resp = proxy_store_request(
            "POST",
            f"/api/v1/orders/{order_id}/cancel",
            json={"reason": body.reason, "staff_name": user.full_name},
        )
        return _proxy_response(resp)
    except Exception:
        raise HTTPException(status_code=502, detail="Servidor de tienda no disponible")
