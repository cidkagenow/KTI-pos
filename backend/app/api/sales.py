import json
import logging
from datetime import date, datetime, time, timezone
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
from app.models.trabajador import Trabajador
from app.schemas.sale import (
    SaleCreate,
    SaleOut,
    SaleListOut,
    SaleItemOut,
    VoidRequest,
    NotaCreditoCreate,
    ConvertirRequest,
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


def _resolve_seller_name(sale: Sale) -> str:
    if sale.trabajador:
        return sale.trabajador.full_name
    if sale.seller:
        return sale.seller.full_name
    return ""


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
        trabajador_id=sale.trabajador_id,
        seller_name=_resolve_seller_name(sale),
        payment_cond=sale.payment_cond,
        payment_method=sale.payment_method,
        cash_received=float(sale.cash_received) if sale.cash_received else None,
        subtotal=float(sale.subtotal),
        igv_amount=float(sale.igv_amount),
        total=float(sale.total),
        status=sale.status,
        notes=sale.notes,
        issue_date=sale.issue_date,
        created_at=sale.created_at,
        updated_at=sale.updated_at,
        sunat_status=sunat_status,
        ref_sale_id=sale.ref_sale_id,
        nc_motivo_code=sale.nc_motivo_code,
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
        client_doc_type=sale.client.doc_type if sale.client else None,
        client_doc_number=sale.client.doc_number if sale.client else None,
        client_address=sale.client.address if sale.client else None,
        warehouse_id=sale.warehouse_id,
        seller_id=sale.seller_id,
        trabajador_id=sale.trabajador_id,
        seller_name=_resolve_seller_name(sale),
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
        updated_at=sale.updated_at,
        items=items,
        ref_sale_id=sale.ref_sale_id,
        nc_motivo_code=sale.nc_motivo_code,
        nc_motivo_text=sale.nc_motivo_text,
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
        .outerjoin(User, Sale.seller_id == User.id)
        .outerjoin(Trabajador, Sale.trabajador_id == Trabajador.id)
        .options(
            joinedload(Sale.client),
            joinedload(Sale.seller),
            joinedload(Sale.trabajador),
        )
    )
    _lima = sa_func.timezone("America/Lima", Sale.created_at)
    if date_from:
        query = query.filter(sa_func.date(_lima) >= date_from)
    if date_to:
        query = query.filter(sa_func.date(_lima) <= date_to)
    if doc_type:
        query = query.filter(Sale.doc_type == doc_type)
    if series:
        query = query.filter(Sale.series == series)
    if client_id is not None:
        query = query.filter(Sale.client_id == client_id)
    if warehouse_id is not None:
        query = query.filter(Sale.warehouse_id == warehouse_id)
    if seller_id is not None:
        # seller_id filter: match either legacy seller_id or trabajador_id
        query = query.filter(
            or_(Sale.seller_id == seller_id, Sale.trabajador_id == seller_id)
        )
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.filter(Sale.status.in_(statuses))

    total = query.count()
    offset = (page - 1) * limit
    sales = query.order_by(Sale.doc_number.desc().nulls_last(), Sale.id.desc()).offset(offset).limit(limit).all()

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

    # Validate series exists and is active (number assigned at facturación)
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
        if data.doc_type != "NOTA_VENTA":
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
        doc_number=None,
        client_id=data.client_id,
        warehouse_id=data.warehouse_id,
        seller_id=data.seller_id,
        trabajador_id=data.trabajador_id,
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
    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)


# Motivos that return stock to warehouse
NC_STOCK_RETURN_MOTIVOS = {"01", "04"}


@router.post("/nota-credito", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_nota_credito(
    data: NotaCreditoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a Nota de Credito referencing an existing FACTURADO sale."""
    # Validate original sale
    ref_sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller), joinedload(Sale.trabajador))
        .filter(Sale.id == data.ref_sale_id)
        .first()
    )
    if ref_sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta original no encontrada",
        )
    if ref_sale.status != "FACTURADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden crear notas de credito para ventas FACTURADAS",
        )

    # Build a map of original items: product_id -> max quantity
    orig_items = {item.product_id: item for item in ref_sale.items}

    # Calculate already-returned quantities from previous NCs for this ref_sale
    prev_ncs = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(
            Sale.ref_sale_id == ref_sale.id,
            Sale.doc_type == "NOTA_CREDITO",
            Sale.status.in_(("PREVENTA", "FACTURADO")),
        )
        .all()
    )
    already_returned: dict[int, int] = {}
    for nc in prev_ncs:
        for item in nc.items:
            already_returned[item.product_id] = already_returned.get(item.product_id, 0) + item.quantity

    # Validate NC items are subset of original
    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nota de credito debe tener al menos un item",
        )

    sale_items = []
    grand_total = Decimal("0")
    for idx, nc_item in enumerate(data.items):
        orig = orig_items.get(nc_item.product_id)
        if orig is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Producto ID {nc_item.product_id} no existe en la venta original",
            )
        available = orig.quantity - already_returned.get(nc_item.product_id, 0)
        if nc_item.quantity > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cantidad a devolver ({nc_item.quantity}) excede lo disponible ({available}) para producto {orig.product_name}",
            )
        if nc_item.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cantidad debe ser mayor a 0 para producto {orig.product_name}",
            )
        line_total = calc_line_total(
            nc_item.quantity,
            Decimal(str(nc_item.unit_price)),
            Decimal(str(nc_item.discount_pct)),
        )
        grand_total += line_total
        product = db.query(Product).filter(Product.id == nc_item.product_id).first()
        sale_items.append(
            SaleItem(
                product_id=nc_item.product_id,
                quantity=nc_item.quantity,
                unit_price=Decimal(str(nc_item.unit_price)),
                discount_pct=Decimal(str(nc_item.discount_pct)),
                line_total=line_total,
                sort_order=idx,
                product_code=orig.product_code,
                product_name=orig.product_name,
                brand_name=orig.brand_name,
                presentation=orig.presentation,
            )
        )

    subtotal, igv_amount, total = calc_igv(grand_total)

    # Get NC series — must start with "F" for facturas or "B" for boletas (SUNAT rule)
    ref_prefix = "F" if ref_sale.doc_type == "FACTURA" else "B"
    doc_series = (
        db.query(DocumentSeries)
        .filter(
            DocumentSeries.doc_type == "NOTA_CREDITO",
            DocumentSeries.is_active == True,
            DocumentSeries.series.like(f"{ref_prefix}%"),
        )
        .first()
    )
    if doc_series is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No hay serie activa de NOTA_CREDITO que empiece con '{ref_prefix}' "
                   f"(requerido para {ref_sale.doc_type}). Cree una en Configuracion (ej: {ref_prefix}N01).",
        )
    nc = Sale(
        doc_type="NOTA_CREDITO",
        series=doc_series.series,
        doc_number=None,
        client_id=ref_sale.client_id,
        warehouse_id=ref_sale.warehouse_id,
        seller_id=ref_sale.seller_id,
        created_by=current_user.id,
        payment_cond=ref_sale.payment_cond,
        payment_method=ref_sale.payment_method,
        subtotal=subtotal,
        igv_amount=igv_amount,
        total=total,
        status="PREVENTA",
        notes=f"NC motivo: {data.nc_motivo_code} - {data.nc_motivo_text}",
        issue_date=date.today(),
        ref_sale_id=ref_sale.id,
        nc_motivo_code=data.nc_motivo_code,
        nc_motivo_text=data.nc_motivo_text,
        items=sale_items,
    )

    db.add(nc)
    db.commit()
    db.refresh(nc)
    return _sale_to_out(nc)


@router.get("/{sale_id}/nc-disponible")
def get_nc_available(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get available quantities for NC creation (original - already returned)."""
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(Sale.id == sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")

    prev_ncs = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(
            Sale.ref_sale_id == sale.id,
            Sale.doc_type == "NOTA_CREDITO",
            Sale.status.in_(("PREVENTA", "FACTURADO")),
        )
        .all()
    )
    already_returned: dict[int, int] = {}
    for nc in prev_ncs:
        for item in nc.items:
            already_returned[item.product_id] = already_returned.get(item.product_id, 0) + item.quantity

    return {
        "items": [
            {
                "product_id": item.product_id,
                "orig_quantity": item.quantity,
                "already_returned": already_returned.get(item.product_id, 0),
                "available": item.quantity - already_returned.get(item.product_id, 0),
            }
            for item in sale.items
        ]
    }


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller), joinedload(Sale.trabajador))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    out = _sale_to_out(sale)
    # Fetch sunat_hash from SunatDocument (prefer the one with a hash)
    sunat_doc = (
        db.query(SunatDocument)
        .filter(SunatDocument.sale_id == sale.id, SunatDocument.sunat_hash.isnot(None), SunatDocument.sunat_hash != "")
        .order_by(SunatDocument.id.desc())
        .first()
    )
    if sunat_doc:
        out.sunat_hash = sunat_doc.sunat_hash
    return out


@router.put("/{sale_id}", response_model=SaleOut)
def update_sale(
    sale_id: int,
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller), joinedload(Sale.trabajador))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    if sale.status not in ("PREVENTA", "EMITIDO"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar ventas en estado PREVENTA o EMITIDO",
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
        if sale.doc_type != "NOTA_VENTA":
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

    # Allow changing doc_type and series for PREVENTA sales
    if sale.status == "PREVENTA" and (data.doc_type != sale.doc_type or data.series != sale.series):
        new_series = (
            db.query(DocumentSeries)
            .filter(
                DocumentSeries.doc_type == data.doc_type,
                DocumentSeries.series == data.series,
                DocumentSeries.is_active == True,
            )
            .first()
        )
        if new_series is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Serie de documento no encontrada o inactiva",
            )
        # SUNAT rule: facturas require client with RUC
        if data.doc_type == "FACTURA" and client.doc_type != "RUC":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las facturas solo se pueden emitir a clientes con RUC.",
            )
        sale.doc_type = data.doc_type
        sale.series = data.series

    sale.client_id = data.client_id
    sale.warehouse_id = data.warehouse_id
    sale.seller_id = data.seller_id
    sale.trabajador_id = data.trabajador_id
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


@router.post("/{sale_id}/emitir-nv", response_model=SaleOut)
def emitir_nota_venta(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Emit (finalize) a Nota de Venta: assigns doc_number, sets status=EMITIDO. No stock deduction."""
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller), joinedload(Sale.trabajador))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    if sale.doc_type != "NOTA_VENTA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden emitir Notas de Venta con este endpoint",
        )
    if sale.status != "PREVENTA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden emitir Notas de Venta en estado PREVENTA",
        )

    # Assign document number from NV series
    doc_series = (
        db.query(DocumentSeries)
        .filter(
            DocumentSeries.doc_type == "NOTA_VENTA",
            DocumentSeries.series == sale.series,
            DocumentSeries.is_active == True,
        )
        .with_for_update()
        .first()
    )
    if doc_series is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serie de Nota de Venta no encontrada o inactiva",
        )
    sale.doc_number = doc_series.next_number
    doc_series.next_number += 1
    sale.status = "EMITIDO"
    sale.issue_date = date.today()

    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)


@router.post("/{sale_id}/facturar", response_model=dict)
def facturar_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    # Lock the sale row to prevent double-facturación from concurrent requests
    sale = (
        db.query(Sale)
        .filter(Sale.id == sale_id)
        .with_for_update()
        .first()
    )
    if sale:
        # Load relationships after acquiring lock
        db.refresh(sale, attribute_names=["items", "client", "seller"])
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

    if sale.doc_type == "NOTA_VENTA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las Notas de Venta no se pueden facturar directamente. Use 'Convertir' para cambiarla a Boleta o Factura primero.",
        )

    # Block facturar-ing boletas if today's resumen was already sent
    if sale.doc_type == "BOLETA":
        from zoneinfo import ZoneInfo
        lima_today = datetime.now(ZoneInfo("America/Lima")).date()
        today_ref = datetime.combine(lima_today, time(12, 0), tzinfo=timezone.utc)
        resumen_for_today = (
            db.query(SunatDocument)
            .filter(
                SunatDocument.sale_id.is_(None),
                SunatDocument.doc_category == "RESUMEN",
                SunatDocument.sunat_status.in_(["ACEPTADO", "PENDIENTE"]),
                SunatDocument.reference_date == today_ref,
            )
            .first()
        )
        if resumen_for_today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede facturar boletas hoy. El resumen diario ya fue enviado. Las nuevas boletas se pueden facturar mañana.",
            )

    # For NC: eagerly load the referenced sale (needed for SUNAT XML)
    if sale.doc_type == "NOTA_CREDITO" and sale.ref_sale_id:
        sale.ref_sale = (
            db.query(Sale)
            .options(joinedload(Sale.client))
            .filter(Sale.id == sale.ref_sale_id)
            .first()
        )

    # SUNAT rule: facturas require client with RUC
    if sale.doc_type == "FACTURA" and sale.client.doc_type != "RUC":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las facturas solo se pueden emitir a clientes con RUC. "
                   "Use boleta para clientes con DNI u otro documento.",
        )

    # Assign real document number at facturación time
    doc_series = (
        db.query(DocumentSeries)
        .filter(
            DocumentSeries.doc_type == sale.doc_type,
            DocumentSeries.series == sale.series,
            DocumentSeries.is_active == True,
        )
        .with_for_update()
        .first()
    )
    if doc_series is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serie no encontrada o inactiva",
        )
    sale.doc_number = doc_series.next_number
    doc_series.next_number += 1

    sale.status = "FACTURADO"
    sale.issue_date = date.today()
    db.flush()

    # Deduct stock (preventas don't touch inventory — only facturación does)
    if sale.doc_type != "NOTA_CREDITO":
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
                created_by=_user.id,
            ))
        db.flush()

    # If this is a NOTA_CREDITO with stock-return motivo, return stock
    if sale.doc_type == "NOTA_CREDITO" and sale.nc_motivo_code in NC_STOCK_RETURN_MOTIVOS:
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
                movement_type="NC_RETURN",
                quantity=item.quantity,
                reference_type="SALE",
                reference_id=sale.id,
                notes=f"Nota de Credito #{sale.series}-{sale.doc_number or sale.id} (motivo {sale.nc_motivo_code})",
                created_by=_user.id,
            ))
        db.flush()

    # Auto-send/sign for SUNAT
    sunat_status = None
    sunat_description = None
    sunat_hash = None
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
            sunat_hash = doc.sunat_hash

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

    elif sale.doc_type == "NOTA_CREDITO":
        try:
            from app.services.sunat_service import send_nota_credito_to_sunat

            parsed = send_nota_credito_to_sunat(sale)

            now = datetime.now(timezone.utc)
            doc = SunatDocument(
                sale_id=sale.id,
                doc_category="NOTA_CREDITO",
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
            sunat_hash = doc.sunat_hash

        except Exception as e:
            logger.error("SUNAT NC send failed for sale %s: %s", sale.id, str(e))
            sunat_status = "ERROR"
            sunat_description = str(e)

    elif sale.doc_type == "BOLETA":
        # Sign XML to get hash for printed receipt (sent later in Resumen Diario)
        try:
            from app.services.sunat_service import sign_document

            parsed = sign_document(sale)

            now = datetime.now(timezone.utc)
            doc = SunatDocument(
                sale_id=sale.id,
                doc_category="BOLETA",
                reference_date=now,
                sunat_status=parsed.get("sunat_status", "PENDIENTE"),
                sunat_description=parsed.get("sunat_description"),
                sunat_hash=parsed.get("sunat_hash"),
                sunat_cdr_url="",
                sunat_xml_url=parsed.get("sunat_xml_url"),
                sunat_pdf_url="",
                ticket="",
                raw_request="",
                raw_response="",
                attempt_count=0,
                last_attempt_at=now,
                sent_by=_user.id,
            )
            db.add(doc)
            db.flush()

            sunat_status = doc.sunat_status
            sunat_description = doc.sunat_description
            sunat_hash = doc.sunat_hash

        except Exception as e:
            logger.error("XML signing failed for boleta %s: %s", sale.id, str(e))
            sunat_status = "ERROR"
            sunat_description = str(e)

    db.commit()
    db.refresh(sale)

    result = _sale_to_out(sale).model_dump()
    result["sunat_status"] = sunat_status
    result["sunat_description"] = sunat_description
    result["sunat_hash"] = sunat_hash
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
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller), joinedload(Sale.trabajador))
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

    # Block voiding a boleta if its resumen was accepted TODAY.
    # Same-day annulment is only allowed if the boleta was never sent (NO_ENVIADA/PENDIENTE).
    if sale.status == "FACTURADO" and sale.doc_type == "BOLETA":
        today_start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
        accepted_today = (
            db.query(SunatDocument)
            .filter(
                SunatDocument.sale_id == sale.id,
                SunatDocument.doc_category == "RESUMEN",
                SunatDocument.sunat_status == "ACEPTADO",
                SunatDocument.last_attempt_at >= today_start,
            )
            .first()
        )
        if accepted_today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede anular esta boleta hoy. El resumen diario ya fue aceptado por SUNAT. Puede anularla a partir de mañana.",
            )

    # Return stock only for FACTURADO sales (preventas/emitidos never deducted stock)
    if sale.status == "FACTURADO" and sale.doc_type not in ("NOTA_VENTA", "NOTA_CREDITO"):
        # BOLETA/FACTURA: return stock that was deducted at facturar
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

    # NOTA_CREDITO: reverse the stock return (re-deduct) if motivo was 01/04
    if sale.status == "FACTURADO" and sale.doc_type == "NOTA_CREDITO" and sale.nc_motivo_code in NC_STOCK_RETURN_MOTIVOS:
        for item in sale.items:
            inv = (
                db.query(Inventory)
                .filter(Inventory.product_id == item.product_id, Inventory.warehouse_id == sale.warehouse_id)
                .first()
            )
            if inv:
                inv.quantity -= item.quantity
            db.add(InventoryMovement(
                product_id=item.product_id,
                warehouse_id=sale.warehouse_id,
                movement_type="VOID_NC_REVERSE",
                quantity=-item.quantity,
                reference_type="SALE",
                reference_id=sale.id,
                notes=f"Anulación NC #{sale.series}-{sale.doc_number} (revierte devolución)",
                created_by=current_user.id,
            ))

    # If voiding a FACTURADO boleta that was never sent to SUNAT (still PENDIENTE),
    # mark the SunatDocument as NO_ENVIADA so it doesn't show as "PENDIENTE" forever.
    if sale.status == "FACTURADO" and sale.doc_type == "BOLETA":
        pending_doc = (
            db.query(SunatDocument)
            .filter(
                SunatDocument.sale_id == sale.id,
                SunatDocument.doc_category == "BOLETA",
                SunatDocument.sunat_status == "PENDIENTE",
            )
            .first()
        )
        if pending_doc:
            pending_doc.sunat_status = "NO_ENVIADA"
            pending_doc.sunat_description = "Anulada antes de enviar a SUNAT"

    sale.status = "ANULADO"
    sale.voided_reason = data.reason
    sale.voided_by = current_user.id
    sale.voided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)


@router.delete("/{sale_id}")
def delete_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller), joinedload(Sale.trabajador))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    allowed_statuses = ("PREVENTA", "EMITIDO") if _user.role == "ADMIN" else ("PREVENTA",)
    if sale.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar preventas" if _user.role != "ADMIN" else "Solo se pueden eliminar ventas en estado PREVENTA o EMITIDO",
        )

    # Preventas/emitidos never deducted stock — hard delete from DB
    for item in sale.items:
        db.delete(item)
    db.delete(sale)
    db.commit()
    return {"detail": "Venta eliminada"}


@router.post("/{sale_id}/convertir", response_model=SaleOut)
def convertir_sale(
    sale_id: int,
    data: ConvertirRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Convert a NOTA_VENTA to BOLETA or FACTURA. Stock is deducted at this point."""
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client), joinedload(Sale.seller), joinedload(Sale.trabajador))
        .filter(Sale.id == sale_id)
        .first()
    )
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )
    if sale.doc_type != "NOTA_VENTA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden convertir Notas de Venta",
        )
    if sale.status not in ("PREVENTA", "EMITIDO"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden convertir ventas en estado PREVENTA o EMITIDO",
        )
    if data.target_doc_type not in ("BOLETA", "FACTURA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de documento destino debe ser BOLETA o FACTURA",
        )

    # Cash must cover total for EFECTIVO payments
    if sale.payment_method == "EFECTIVO" and sale.cash_received is not None and sale.cash_received < sale.total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El efectivo recibido es menor al total. Edite la nota de venta antes de convertir.",
        )

    # SUNAT rule: facturas require client with RUC
    if data.target_doc_type == "FACTURA" and sale.client.doc_type != "RUC":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las facturas solo se pueden emitir a clientes con RUC. "
                   "Use boleta para clientes con DNI u otro documento.",
        )

    # Get target series
    doc_series = (
        db.query(DocumentSeries)
        .filter(
            DocumentSeries.doc_type == data.target_doc_type,
            DocumentSeries.series == data.target_series,
            DocumentSeries.is_active == True,
        )
        .first()
    )
    if doc_series is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Serie {data.target_series} no encontrada o inactiva para {data.target_doc_type}",
        )

    # Save original NV reference for audit
    original_ref = f"NV {sale.series}-{sale.doc_number or sale.id}"
    sale.notes = f"[Convertido de {original_ref}] {sale.notes or ''}".strip()

    # Change doc_type/series, reset to PREVENTA — doc_number assigned later at facturar
    # Stock is NOT deducted here — only at facturar
    sale.doc_type = data.target_doc_type
    sale.series = data.target_series
    sale.doc_number = None
    sale.status = "PREVENTA"

    db.commit()
    db.refresh(sale)
    return _sale_to_out(sale)
