import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, or_

from app.database import get_db
from app.models.sale import Sale, SaleItem, DocumentSeries
from app.models.client import Client
from app.models.product import Product
from app.models.user import User
from app.models.inventory import Inventory, InventoryMovement
from app.models.sunat import SunatDocument
from app.schemas.sale import (
    SaleCreate,
    SaleOut,
    SaleListOut,
    SaleItemOut,
    VoidRequest,
)
from app.utils.igv import calc_igv, calc_line_total
from app.api.deps import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_total_stock(db: Session, product_id: int) -> int:
    result = db.query(sa_func.coalesce(sa_func.sum(Inventory.quantity), 0)).filter(
        Inventory.product_id == product_id
    ).scalar()
    return int(result)


def _sale_to_list_out(sale: Sale, sunat_status: str | None = None) -> SaleListOut:
    return SaleListOut(
        id=sale.id,
        doc_type=sale.doc_type,
        series=sale.series,
        doc_number=sale.doc_number,
        client_id=sale.client_id,
        client_name=sale.client.business_name if sale.client else "",
        warehouse_id=sale.warehouse_id,
        seller_id=sale.seller_id,
        seller_name=sale.seller.full_name if sale.seller else "",
        payment_cond=sale.payment_cond,
        payment_method=sale.payment_method,
        subtotal=float(sale.subtotal),
        igv_amount=float(sale.igv_amount),
        total=float(sale.total),
        status=sale.status,
        notes=sale.notes,
        issue_date=sale.issue_date,
        created_at=sale.created_at,
        sunat_status=sunat_status,
    )


def _sale_to_out(sale: Sale) -> SaleOut:
    items = [
        SaleItemOut(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=float(item.unit_price),
            discount_pct=float(item.discount_pct),
            line_total=float(item.line_total),
            product_code=item.product_code or "",
            product_name=item.product_name or "",
            brand_name=item.brand_name,
            presentation=item.presentation,
        )
        for item in sale.items
    ]
    return SaleOut(
        id=sale.id,
        doc_type=sale.doc_type,
        series=sale.series,
        doc_number=sale.doc_number,
        client_id=sale.client_id,
        client_name=sale.client.business_name if sale.client else "",
        warehouse_id=sale.warehouse_id,
        seller_id=sale.seller_id,
        seller_name=sale.seller.full_name if sale.seller else "",
        payment_cond=sale.payment_cond,
        payment_method=sale.payment_method,
        cash_received=float(sale.cash_received) if sale.cash_received else None,
        cash_change=float(sale.cash_change) if sale.cash_change else None,
        max_discount_pct=float(sale.max_discount_pct) if sale.max_discount_pct else None,
        subtotal=float(sale.subtotal),
        igv_amount=float(sale.igv_amount),
        total=float(sale.total),
        status=sale.status,
        notes=sale.notes,
        issue_date=sale.issue_date,
        created_at=sale.created_at,
        items=items,
    )


@router.get("", response_model=dict)
def list_sales(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    doc_type: str | None = Query(None),
    series: str | None = Query(None),
    client_id: int | None = Query(None),
    warehouse_id: int | None = Query(None),
    seller_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = (
        db.query(Sale)
        .join(Client, Sale.client_id == Client.id)
        .join(User, Sale.seller_id == User.id)
        .options(joinedload(Sale.client), joinedload(Sale.seller))
    )
    if date_from:
        query = query.filter(Sale.created_at >= date_from)
    if date_to:
        query = query.filter(Sale.created_at <= date_to + " 23:59:59")
    if doc_type:
        query = query.filter(Sale.doc_type == doc_type)
    if series:
        query = query.filter(Sale.series == series)
    if client_id is not None:
        query = query.filter(Sale.client_id == client_id)
    if warehouse_id is not None:
        query = query.filter(Sale.warehouse_id == warehouse_id)
    if seller_id is not None:
        query = query.filter(Sale.seller_id == seller_id)
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.filter(Sale.status.in_(statuses))

    total = query.count()
    offset = (page - 1) * limit
    sales = query.order_by(Sale.created_at.desc()).offset(offset).limit(limit).all()

    # Batch-fetch SUNAT statuses for these sales
    sale_ids = [s.id for s in sales]
    sunat_map: dict[int, str] = {}
    if sale_ids:
        sunat_docs = (
            db.query(SunatDocument.sale_id, SunatDocument.sunat_status)
            .filter(SunatDocument.sale_id.in_(sale_ids))
            .order_by(SunatDocument.created_at.desc())
            .all()
        )
        for doc in sunat_docs:
            if doc.sale_id not in sunat_map:
                sunat_map[doc.sale_id] = doc.sunat_status

    return {
        "data": [_sale_to_list_out(s, sunat_map.get(s.id)) for s in sales],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a sale (placeholder — will be refactored to sale_service.create_sale).
    Handles doc numbering, IGV calculation, and item snapshot directly.
    """
    # Validate client exists
    client = db.query(Client).filter(Client.id == data.client_id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    # SUNAT rule: facturas require client with RUC
    if data.doc_type == "FACTURA" and client.doc_type != "RUC":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las facturas solo se pueden emitir a clientes con RUC. "
                   "Use boleta para clientes con DNI u otro documento.",
        )

    # Get next doc number from series
    doc_series = (
        db.query(DocumentSeries)
        .filter(
            DocumentSeries.doc_type == data.doc_type,
            DocumentSeries.series == data.series,
            DocumentSeries.is_active == True,
        )
        .first()
    )
    if doc_series is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serie de documento no encontrada o inactiva",
        )
    doc_number = doc_series.next_number
    doc_series.next_number += 1

    # Build sale items and calculate totals
    sale_items = []
    grand_total = Decimal("0")
    for idx, item_in in enumerate(data.items):
        product = db.query(Product).filter(Product.id == item_in.product_id).first()
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {item_in.product_id} no encontrado",
            )
        total_stock = _get_total_stock(db, product.id)
        if total_stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Producto '{product.name}' sin stock disponible (stock: {total_stock})",
            )
        line_total = calc_line_total(
            item_in.quantity,
            Decimal(str(item_in.unit_price)),
            Decimal(str(item_in.discount_pct)),
        )
        grand_total += line_total
        sale_items.append(
            SaleItem(
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                unit_price=Decimal(str(item_in.unit_price)),
                discount_pct=Decimal(str(item_in.discount_pct)),
                line_total=line_total,
                sort_order=idx,
                product_code=product.code,
                product_name=product.name,
                brand_name=product.brand.name if product.brand else None,
                presentation=product.presentation,
            )
        )

    # IGV calculation
    subtotal, igv_amount, total = calc_igv(grand_total)

    sale = Sale(
        doc_type=data.doc_type,
        series=data.series,
        doc_number=doc_number,
        client_id=data.client_id,
        warehouse_id=data.warehouse_id,
        seller_id=data.seller_id,
        created_by=current_user.id,
        payment_cond=data.payment_cond,
        payment_method=data.payment_method,
        cash_received=Decimal(str(data.cash_received)) if data.cash_received else None,
        cash_change=Decimal(str(data.cash_change)) if data.cash_change else None,
        max_discount_pct=Decimal(str(data.max_discount_pct)) if data.max_discount_pct else Decimal("0"),
        subtotal=subtotal,
        igv_amount=igv_amount,
        total=total,
        status="PREVENTA",
        notes=data.notes,
        issue_date=data.issue_date or date.today(),
        items=sale_items,
    )

    db.add(sale)
    db.flush()

    # Deduct stock for each item
    for item in sale.items:
        inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == item.product_id, Inventory.warehouse_id == sale.warehouse_id)
            .first()
        )
        if inv is None:
            inv = Inventory(product_id=item.product_id, warehouse_id=sale.warehouse_id, quantity=0)
            db.add(inv)
            db.flush()
        inv.quantity -= item.quantity
        db.add(InventoryMovement(
            product_id=item.product_id,
            warehouse_id=sale.warehouse_id,
            movement_type="SALE",
            quantity=-item.quantity,
            reference_type="SALE",
            reference_id=sale.id,
            notes=f"Venta #{sale.series}-{sale.doc_number}",
            created_by=current_user.id,
        ))

    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    return _sale_to_out(sale)


@router.put("/{sale_id}", response_model=SaleOut)
def update_sale(
    sale_id: int,
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    if sale.status != "PREVENTA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar ventas en estado PREVENTA",
        )

    # Validate client
    client = db.query(Client).filter(Client.id == data.client_id).first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    # Clear existing items
    for item in sale.items:
        db.delete(item)

    # Rebuild items
    sale_items = []
    grand_total = Decimal("0")
    for idx, item_in in enumerate(data.items):
        product = db.query(Product).filter(Product.id == item_in.product_id).first()
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {item_in.product_id} no encontrado",
            )
        total_stock = _get_total_stock(db, product.id)
        if total_stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Producto '{product.name}' sin stock disponible (stock: {total_stock})",
            )
        line_total = calc_line_total(
            item_in.quantity,
            Decimal(str(item_in.unit_price)),
            Decimal(str(item_in.discount_pct)),
        )
        grand_total += line_total
        sale_items.append(
            SaleItem(
                sale_id=sale.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                unit_price=Decimal(str(item_in.unit_price)),
                discount_pct=Decimal(str(item_in.discount_pct)),
                line_total=line_total,
                sort_order=idx,
                product_code=product.code,
                product_name=product.name,
                brand_name=product.brand.name if product.brand else None,
                presentation=product.presentation,
            )
        )

    subtotal, igv_amount, total = calc_igv(grand_total)

    sale.client_id = data.client_id
    sale.warehouse_id = data.warehouse_id
    sale.seller_id = data.seller_id
    sale.payment_cond = data.payment_cond
    sale.payment_method = data.payment_method
    sale.cash_received = Decimal(str(data.cash_received)) if data.cash_received else None
    sale.cash_change = Decimal(str(data.cash_change)) if data.cash_change else None
    sale.max_discount_pct = Decimal(str(data.max_discount_pct)) if data.max_discount_pct else Decimal("0")
    sale.subtotal = subtotal
    sale.igv_amount = igv_amount
    sale.total = total
    sale.notes = data.notes
    if data.issue_date:
        sale.issue_date = data.issue_date
    sale.items = sale_items

    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)


@router.post("/{sale_id}/facturar", response_model=dict)
def facturar_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    if sale.status != "PREVENTA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden facturar ventas en estado PREVENTA",
        )

    # SUNAT rule: facturas require client with RUC
    if sale.doc_type == "FACTURA" and sale.client.doc_type != "RUC":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las facturas solo se pueden emitir a clientes con RUC. "
                   "Use boleta para clientes con DNI u otro documento.",
        )

    sale.status = "FACTURADO"
    sale.issue_date = date.today()
    db.flush()

    # Auto-send factura to SUNAT (boletas go via resumen diario)
    sunat_status = None
    sunat_description = None
    if sale.doc_type == "FACTURA":
        try:
            from app.services.sunat_service import send_factura_to_sunat
            from app.services.email_service import send_factura_email

            parsed = send_factura_to_sunat(sale)

            now = datetime.now(timezone.utc)
            doc = SunatDocument(
                sale_id=sale.id,
                doc_category="FACTURA",
                reference_date=now,
                sunat_status=parsed.get("sunat_status", "ERROR"),
                sunat_description=parsed.get("sunat_description"),
                sunat_hash=parsed.get("sunat_hash"),
                sunat_cdr_url=parsed.get("sunat_cdr_url"),
                sunat_xml_url=parsed.get("sunat_xml_url"),
                sunat_pdf_url=parsed.get("sunat_pdf_url"),
                ticket=parsed.get("ticket"),
                raw_request="",
                raw_response=json.dumps(parsed, ensure_ascii=False),
                attempt_count=1,
                last_attempt_at=now,
                sent_by=_user.id,
            )
            db.add(doc)
            db.flush()

            sunat_status = doc.sunat_status
            sunat_description = doc.sunat_description

            # Auto-email if accepted
            if doc.sunat_status == "ACEPTADO" and sale.client.email:
                try:
                    send_factura_email(
                        client_email=sale.client.email,
                        client_name=sale.client.business_name,
                        doc_series=sale.series,
                        doc_number=sale.doc_number,
                        pdf_url=doc.sunat_pdf_url or "",
                        xml_url=doc.sunat_xml_url or "",
                    )
                except Exception as e:
                    logger.error("Email failed for sale %s: %s", sale.id, str(e))

        except Exception as e:
            logger.error("SUNAT send failed for sale %s: %s", sale.id, str(e))
            sunat_status = "ERROR"
            sunat_description = str(e)

    db.commit()
    db.refresh(sale)

    result = _sale_to_out(sale).model_dump()
    result["sunat_status"] = sunat_status
    result["sunat_description"] = sunat_description
    return result


@router.post("/{sale_id}/anular", response_model=SaleOut)
def void_sale(
    sale_id: int,
    data: VoidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    if sale.status == "ANULADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La venta ya está anulada",
        )
    if sale.status == "ELIMINADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La venta está eliminada",
        )
    # Return stock for each item
    for item in sale.items:
        inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == item.product_id, Inventory.warehouse_id == sale.warehouse_id)
            .first()
        )
        if inv:
            inv.quantity += item.quantity
        db.add(InventoryMovement(
            product_id=item.product_id,
            warehouse_id=sale.warehouse_id,
            movement_type="VOID_RETURN",
            quantity=item.quantity,
            reference_type="SALE",
            reference_id=sale.id,
            notes=f"Anulación venta #{sale.series}-{sale.doc_number}",
            created_by=current_user.id,
        ))

    sale.status = "ANULADO"
    sale.voided_reason = data.reason
    sale.voided_by = current_user.id
    sale.voided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)


@router.delete("/{sale_id}", response_model=SaleOut)
def soft_delete_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    if sale.status not in ("PREVENTA",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar ventas en estado PREVENTA",
        )

    # Return stock for each item
    for item in sale.items:
        inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == item.product_id, Inventory.warehouse_id == sale.warehouse_id)
            .first()
        )
        if inv:
            inv.quantity += item.quantity
        db.add(InventoryMovement(
            product_id=item.product_id,
            warehouse_id=sale.warehouse_id,
            movement_type="VOID_RETURN",
            quantity=item.quantity,
            reference_type="SALE",
            reference_id=sale.id,
            notes=f"Eliminación venta #{sale.series}-{sale.doc_number}",
            created_by=_user.id,
        ))

    sale.status = "ELIMINADO"
    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)
