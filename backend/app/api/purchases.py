from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory, InventoryMovement
from app.models.user import User
from app.schemas.purchase import (
    PurchaseOrderCreate,
    PurchaseOrderOut,
    PurchaseOrderItemOut,
)
from app.api.deps import get_current_user, require_admin

router = APIRouter()


def _calc_item_total(qty: int, unit_cost: float, d1: float = 0, d2: float = 0, d3: float = 0, flete: float = 0) -> Decimal:
    price = Decimal(str(unit_cost))
    if d1:
        price = price * (1 - Decimal(str(d1)) / 100)
    if d2:
        price = price * (1 - Decimal(str(d2)) / 100)
    if d3:
        price = price * (1 - Decimal(str(d3)) / 100)
    line = Decimal(str(qty)) * price + Decimal(str(flete)) * Decimal(str(qty))
    return line.quantize(Decimal("0.01"))


def _po_to_out(po: PurchaseOrder) -> PurchaseOrderOut:
    items = [
        PurchaseOrderItemOut(
            id=item.id,
            product_id=item.product_id,
            product_code=item.product_code or (item.product.code if item.product else None),
            product_name=item.product_name or (item.product.name if item.product else ""),
            quantity=item.quantity,
            unit_cost=float(item.unit_cost),
            discount_pct1=float(item.discount_pct1 or 0),
            discount_pct2=float(item.discount_pct2 or 0),
            discount_pct3=float(item.discount_pct3 or 0),
            flete_unit=float(item.flete_unit or 0),
            line_total=float(item.line_total),
        )
        for item in po.items
    ]
    return PurchaseOrderOut(
        id=po.id,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.business_name if po.supplier else "",
        supplier_ruc=po.supplier.ruc if po.supplier else None,
        warehouse_id=po.warehouse_id,
        status=po.status,
        doc_type=po.doc_type,
        doc_number=po.doc_number,
        supplier_doc=po.supplier_doc,
        condicion=po.condicion,
        moneda=po.moneda,
        tipo_cambio=float(po.tipo_cambio) if po.tipo_cambio else None,
        igv_included=po.igv_included,
        subtotal=float(po.subtotal) if po.subtotal else None,
        igv_amount=float(po.igv_amount) if po.igv_amount else None,
        total=float(po.total) if po.total else 0,
        flete=float(po.flete) if po.flete else 0,
        grr_number=po.grr_number,
        notes=po.notes,
        expected_delivery_date=po.expected_delivery_date,
        issue_date=po.issue_date,
        received_at=po.received_at,
        created_at=po.created_at,
        items=items,
    )


@router.get("", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    pos = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            joinedload(PurchaseOrder.supplier),
        )
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )
    return [_po_to_out(po) for po in pos]


@router.post("", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    data: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    supplier = db.query(Supplier).filter(Supplier.id == data.supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    warehouse = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id).first()
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")

    po_items = []
    grand_total = Decimal("0")
    for item_in in data.items:
        product = db.query(Product).filter(Product.id == item_in.product_id).first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Producto con ID {item_in.product_id} no encontrado")
        line_total = _calc_item_total(item_in.quantity, item_in.unit_cost, item_in.discount_pct1, item_in.discount_pct2, item_in.discount_pct3, item_in.flete_unit)
        grand_total += line_total
        po_items.append(
            PurchaseOrderItem(
                product_id=item_in.product_id,
                product_code=product.code,
                product_name=product.name,
                quantity=item_in.quantity,
                unit_cost=Decimal(str(item_in.unit_cost)),
                discount_pct1=Decimal(str(item_in.discount_pct1)),
                discount_pct2=Decimal(str(item_in.discount_pct2)),
                discount_pct3=Decimal(str(item_in.discount_pct3)),
                flete_unit=Decimal(str(item_in.flete_unit)),
                line_total=line_total,
            )
        )

    # Calculate IGV breakdown
    if data.igv_included:
        base = grand_total / Decimal("1.18")
        igv = grand_total - base
    else:
        base = grand_total
        igv = grand_total * Decimal("0.18")
        grand_total = base + igv

    flete_total = Decimal(str(data.flete))

    po = PurchaseOrder(
        supplier_id=data.supplier_id,
        warehouse_id=data.warehouse_id,
        status="DRAFT",
        doc_type=data.doc_type,
        doc_number=data.doc_number,
        supplier_doc=data.supplier_doc,
        condicion=data.condicion,
        moneda=data.moneda,
        tipo_cambio=Decimal(str(data.tipo_cambio)) if data.tipo_cambio else None,
        igv_included=data.igv_included,
        subtotal=base.quantize(Decimal("0.01")),
        igv_amount=igv.quantize(Decimal("0.01")),
        total=(grand_total + flete_total).quantize(Decimal("0.01")),
        flete=flete_total,
        grr_number=data.grr_number,
        notes=data.notes,
        expected_delivery_date=date.fromisoformat(data.expected_delivery_date) if data.expected_delivery_date else None,
        created_by=current_user.id,
        items=po_items,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return _po_to_out(po)


@router.get("/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    po = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            joinedload(PurchaseOrder.supplier),
        )
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada")
    return _po_to_out(po)


@router.put("/{po_id}", response_model=PurchaseOrderOut)
def update_purchase_order(
    po_id: int,
    data: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    po = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            joinedload(PurchaseOrder.supplier),
        )
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada")
    if po.status != "DRAFT":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se pueden editar órdenes en estado DRAFT")

    for item in po.items:
        db.delete(item)

    po_items = []
    grand_total = Decimal("0")
    for item_in in data.items:
        product = db.query(Product).filter(Product.id == item_in.product_id).first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Producto con ID {item_in.product_id} no encontrado")
        line_total = _calc_item_total(item_in.quantity, item_in.unit_cost, item_in.discount_pct1, item_in.discount_pct2, item_in.discount_pct3, item_in.flete_unit)
        grand_total += line_total
        po_items.append(
            PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=item_in.product_id,
                product_code=product.code,
                product_name=product.name,
                quantity=item_in.quantity,
                unit_cost=Decimal(str(item_in.unit_cost)),
                discount_pct1=Decimal(str(item_in.discount_pct1)),
                discount_pct2=Decimal(str(item_in.discount_pct2)),
                discount_pct3=Decimal(str(item_in.discount_pct3)),
                flete_unit=Decimal(str(item_in.flete_unit)),
                line_total=line_total,
            )
        )

    if data.igv_included:
        base = grand_total / Decimal("1.18")
        igv = grand_total - base
    else:
        base = grand_total
        igv = grand_total * Decimal("0.18")
        grand_total = base + igv

    flete_total = Decimal(str(data.flete))

    po.supplier_id = data.supplier_id
    po.warehouse_id = data.warehouse_id
    po.doc_type = data.doc_type
    po.doc_number = data.doc_number
    po.supplier_doc = data.supplier_doc
    po.condicion = data.condicion
    po.moneda = data.moneda
    po.tipo_cambio = Decimal(str(data.tipo_cambio)) if data.tipo_cambio else None
    po.igv_included = data.igv_included
    po.subtotal = base.quantize(Decimal("0.01"))
    po.igv_amount = igv.quantize(Decimal("0.01"))
    po.total = (grand_total + flete_total).quantize(Decimal("0.01"))
    po.flete = flete_total
    po.grr_number = data.grr_number
    po.notes = data.notes
    po.expected_delivery_date = date.fromisoformat(data.expected_delivery_date) if data.expected_delivery_date else None
    po.items = po_items

    db.commit()
    db.refresh(po)
    return _po_to_out(po)


@router.post("/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    po = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            joinedload(PurchaseOrder.supplier),
        )
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada")
    if po.status == "RECEIVED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La orden ya fue recibida")
    if po.status == "CANCELLED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La orden está cancelada")

    for item in po.items:
        inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == item.product_id, Inventory.warehouse_id == po.warehouse_id)
            .first()
        )
        if inv is None:
            inv = Inventory(product_id=item.product_id, warehouse_id=po.warehouse_id, quantity=0)
            db.add(inv)
            db.flush()

        inv.quantity += item.quantity

        # Update product cost price from purchase
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product and item.unit_cost:
            product.cost_price = item.unit_cost

        movement = InventoryMovement(
            product_id=item.product_id,
            warehouse_id=po.warehouse_id,
            movement_type="PURCHASE",
            quantity=item.quantity,
            reference_type="PURCHASE_ORDER",
            reference_id=po.id,
            notes=f"Recepción OC #{po.id}",
            created_by=current_user.id,
        )
        db.add(movement)

    po.status = "RECEIVED"
    po.received_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(po)
    return _po_to_out(po)


@router.delete("/{po_id}", response_model=PurchaseOrderOut)
def cancel_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    po = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            joinedload(PurchaseOrder.supplier),
        )
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada")
    if po.status == "RECEIVED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede cancelar una orden ya recibida")
    po.status = "CANCELLED"
    db.commit()
    db.refresh(po)
    return _po_to_out(po)
