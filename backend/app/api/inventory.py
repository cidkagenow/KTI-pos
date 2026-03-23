from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from app.database import get_db
from app.models.inventory import Inventory, InventoryMovement
from app.models.product import Product
from app.models.purchase import PurchaseOrder
from app.models.sale import Sale
from app.models.warehouse import Warehouse
from app.models.user import User
from app.schemas.inventory import (
    InventoryOut,
    InventoryAdjust,
    InventoryTransfer,
    MovementOut,
    KardexEntry,
    KardexResponse,
)
from app.api.deps import get_current_user, require_admin

router = APIRouter()


def _inv_to_out(inv: Inventory) -> InventoryOut:
    return InventoryOut(
        id=inv.id,
        product_id=inv.product_id,
        product_code=inv.product.code if inv.product else "",
        product_name=inv.product.name if inv.product else "",
        warehouse_id=inv.warehouse_id,
        warehouse_name=inv.warehouse.name if inv.warehouse else "",
        quantity=inv.quantity,
    )


def _mov_to_out(mov: InventoryMovement) -> MovementOut:
    return MovementOut(
        id=mov.id,
        product_id=mov.product_id,
        product_name=mov.product.name if mov.product else "",
        warehouse_id=mov.warehouse_id,
        warehouse_name=mov.warehouse.name if mov.warehouse else "",
        movement_type=mov.movement_type,
        quantity=mov.quantity,
        reference_type=mov.reference_type,
        reference_id=mov.reference_id,
        notes=mov.notes,
        created_at=mov.created_at,
    )


@router.get("", response_model=list[InventoryOut])
def list_inventory(
    warehouse_id: int | None = Query(None),
    low_stock_only: bool = Query(False),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Inventory).join(Product).join(Warehouse)
    if warehouse_id is not None:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    if low_stock_only:
        query = query.filter(Inventory.quantity <= Product.min_stock)
    inventories = query.order_by(Product.name).all()
    return [_inv_to_out(inv) for inv in inventories]


@router.get("/alerts", response_model=list[InventoryOut])
def low_stock_alerts(
    warehouse_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = (
        db.query(Inventory)
        .join(Product)
        .join(Warehouse)
        .filter(Inventory.quantity <= Product.min_stock)
    )
    if warehouse_id is not None:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    inventories = query.order_by(Product.name).all()
    return [_inv_to_out(inv) for inv in inventories]


@router.post("/adjust", response_model=InventoryOut)
def adjust_stock(
    data: InventoryAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Validate product and warehouse
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    warehouse = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id).first()
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén no encontrado",
        )

    # Find or create inventory record
    inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == data.product_id,
            Inventory.warehouse_id == data.warehouse_id,
        )
        .first()
    )
    if inv is None:
        inv = Inventory(
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            quantity=0,
        )
        db.add(inv)
        db.flush()

    old_qty = inv.quantity
    diff = data.new_quantity - old_qty
    inv.quantity = data.new_quantity

    # Record movement
    movement = InventoryMovement(
        product_id=data.product_id,
        warehouse_id=data.warehouse_id,
        movement_type="ADJUSTMENT",
        quantity=diff,
        notes=data.notes or f"Ajuste manual: {old_qty} -> {data.new_quantity}",
        created_by=current_user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(inv)
    return _inv_to_out(inv)


@router.post("/transfer", response_model=dict)
def transfer_stock(
    data: InventoryTransfer,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Validate product
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    # Validate warehouses
    from_wh = db.query(Warehouse).filter(Warehouse.id == data.from_warehouse_id).first()
    if from_wh is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén de origen no encontrado",
        )
    to_wh = db.query(Warehouse).filter(Warehouse.id == data.to_warehouse_id).first()
    if to_wh is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén de destino no encontrado",
        )
    if data.from_warehouse_id == data.to_warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los almacenes de origen y destino deben ser diferentes",
        )
    if data.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cantidad debe ser mayor a 0",
        )

    # Check source stock
    from_inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == data.product_id,
            Inventory.warehouse_id == data.from_warehouse_id,
        )
        .first()
    )
    if from_inv is None or from_inv.quantity < data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock insuficiente en el almacén de origen",
        )

    # Find or create destination inventory
    to_inv = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == data.product_id,
            Inventory.warehouse_id == data.to_warehouse_id,
        )
        .first()
    )
    if to_inv is None:
        to_inv = Inventory(
            product_id=data.product_id,
            warehouse_id=data.to_warehouse_id,
            quantity=0,
        )
        db.add(to_inv)
        db.flush()

    # Update quantities
    from_inv.quantity -= data.quantity
    to_inv.quantity += data.quantity

    # Record movements
    mov_out = InventoryMovement(
        product_id=data.product_id,
        warehouse_id=data.from_warehouse_id,
        movement_type="TRANSFER",
        quantity=-data.quantity,
        notes=f"Transferencia a {to_wh.name}",
        created_by=current_user.id,
    )
    mov_in = InventoryMovement(
        product_id=data.product_id,
        warehouse_id=data.to_warehouse_id,
        movement_type="TRANSFER",
        quantity=data.quantity,
        notes=f"Transferencia desde {from_wh.name}",
        created_by=current_user.id,
    )
    db.add(mov_out)
    db.add(mov_in)
    db.commit()

    db.refresh(from_inv)
    db.refresh(to_inv)

    return {
        "message": "Transferencia realizada",
        "from": _inv_to_out(from_inv).model_dump(),
        "to": _inv_to_out(to_inv).model_dump(),
    }


@router.get("/kardex", response_model=KardexResponse)
def get_kardex(
    product_id: int = Query(...),
    warehouse_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    cost_price = float(product.cost_price or 0)

    # Determine warehouse name
    warehouse_name: str | None = None
    if warehouse_id is not None:
        wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if wh:
            warehouse_name = wh.name

    # Build base query for this product
    base_q = db.query(InventoryMovement).filter(
        InventoryMovement.product_id == product_id,
    )
    if warehouse_id is not None:
        base_q = base_q.filter(InventoryMovement.warehouse_id == warehouse_id)

    # Calculate initial balance (movements before date_from)
    initial_balance_qty: float = 0.0
    if date_from is not None:
        initial_sum = (
            base_q.filter(
                sa_func.date(InventoryMovement.created_at) < date_from
            )
            .with_entities(sa_func.coalesce(sa_func.sum(InventoryMovement.quantity), 0))
            .scalar()
        )
        initial_balance_qty = float(initial_sum)

    initial_balance_cost = initial_balance_qty * cost_price

    # Fetch movements in range
    movements_q = base_q
    if date_from is not None:
        movements_q = movements_q.filter(
            sa_func.date(InventoryMovement.created_at) >= date_from
        )
    if date_to is not None:
        movements_q = movements_q.filter(
            sa_func.date(InventoryMovement.created_at) <= date_to
        )

    movements = movements_q.order_by(InventoryMovement.created_at.asc()).all()

    # Pre-fetch sale references in bulk
    sale_ref_ids = [
        m.reference_id
        for m in movements
        if m.reference_type == "sale" and m.reference_id is not None
    ]
    sale_map: dict[int, Sale] = {}
    if sale_ref_ids:
        sales = db.query(Sale).filter(Sale.id.in_(sale_ref_ids)).all()
        sale_map = {s.id: s for s in sales}

    # Pre-fetch purchase order references in bulk
    po_ref_ids = [
        m.reference_id
        for m in movements
        if m.reference_type == "purchase_order" and m.reference_id is not None
    ]
    po_map: dict[int, PurchaseOrder] = {}
    if po_ref_ids:
        pos = db.query(PurchaseOrder).filter(PurchaseOrder.id.in_(po_ref_ids)).all()
        po_map = {p.id: p for p in pos}

    # Doc type mapping for sales
    sale_doc_type_map = {
        "FACTURA": "01",
        "BOLETA": "03",
        "NOTA_CREDITO": "07",
        "NOTA_VENTA": "NV",
    }

    running_qty = initial_balance_qty
    entries: list[KardexEntry] = []

    for mov in movements:
        qty = float(mov.quantity)
        entrada_qty = qty if qty > 0 else 0.0
        salida_qty = abs(qty) if qty < 0 else 0.0
        entrada_cost_total = entrada_qty * cost_price
        salida_cost_total = salida_qty * cost_price
        running_qty += qty

        # Resolve document reference
        doc_type: str | None = None
        doc_series: str | None = None
        doc_number: str | None = None

        if mov.reference_type == "sale" and mov.reference_id in sale_map:
            sale = sale_map[mov.reference_id]
            doc_type = sale_doc_type_map.get(sale.doc_type, sale.doc_type)
            doc_series = sale.series
            doc_number = str(sale.doc_number) if sale.doc_number is not None else None
        elif mov.reference_type == "purchase_order" and mov.reference_id in po_map:
            po = po_map[mov.reference_id]
            doc_type = "OC"
            doc_series = None
            doc_number = str(po.id)

        entries.append(
            KardexEntry(
                date=mov.created_at.strftime("%Y-%m-%d"),
                movement_type=mov.movement_type,
                doc_type=doc_type,
                doc_series=doc_series,
                doc_number=doc_number,
                entrada_qty=entrada_qty,
                entrada_cost_unit=cost_price if entrada_qty > 0 else 0.0,
                entrada_cost_total=entrada_cost_total,
                salida_qty=salida_qty,
                salida_cost_unit=cost_price if salida_qty > 0 else 0.0,
                salida_cost_total=salida_cost_total,
                saldo_qty=running_qty,
                saldo_cost_unit=cost_price,
                saldo_cost_total=running_qty * cost_price,
            )
        )

    return KardexResponse(
        product_code=product.code,
        product_name=product.name,
        warehouse_name=warehouse_name,
        initial_balance_qty=initial_balance_qty,
        initial_balance_cost=initial_balance_cost,
        entries=entries,
    )


@router.get("/movements", response_model=list[MovementOut])
def list_movements(
    product_id: int | None = Query(None),
    warehouse_id: int | None = Query(None),
    movement_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = (
        db.query(InventoryMovement)
        .join(Product, InventoryMovement.product_id == Product.id)
        .join(Warehouse, InventoryMovement.warehouse_id == Warehouse.id)
    )
    if product_id is not None:
        query = query.filter(InventoryMovement.product_id == product_id)
    if warehouse_id is not None:
        query = query.filter(InventoryMovement.warehouse_id == warehouse_id)
    if movement_type:
        query = query.filter(InventoryMovement.movement_type == movement_type)
    movements = query.order_by(InventoryMovement.created_at.desc()).limit(limit).all()
    return [_mov_to_out(m) for m in movements]
