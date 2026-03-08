from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app.models.product import Product, Brand, Category
from app.models.inventory import Inventory
from app.models.purchase import PurchaseOrder, PurchaseOrderItem
from app.models.user import User
from app.schemas.product import ProductOut, ProductCreate, ProductUpdate, ProductSearch
from app.api.deps import get_current_user, require_admin

router = APIRouter()


def _get_total_stock(db: Session, product_id: int) -> int:
    result = db.query(func.coalesce(func.sum(Inventory.quantity), 0)).filter(
        Inventory.product_id == product_id
    ).scalar()
    return int(result)


def _get_pending_order_info(db: Session, product_id: int) -> tuple[int | None, date | None]:
    """Return (total_qty_on_order, earliest_eta) from DRAFT purchase orders."""
    row = (
        db.query(
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0),
            func.min(PurchaseOrder.expected_delivery_date),
        )
        .join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        .filter(
            PurchaseOrderItem.product_id == product_id,
            PurchaseOrder.status == "DRAFT",
        )
        .first()
    )
    qty = int(row[0]) if row else 0
    eta = row[1] if row else None
    if qty == 0:
        return None, None
    return qty, eta


def _product_to_out(product: Product, db: Session) -> ProductOut:
    """Convert a Product model to ProductOut, including brand_name, category_name, and total_stock."""
    total_stock = _get_total_stock(db, product.id)
    on_order_qty, on_order_eta = (None, None)
    if total_stock <= 0:
        on_order_qty, on_order_eta = _get_pending_order_info(db, product.id)
    return ProductOut(
        id=product.id,
        code=product.code,
        name=product.name,
        brand_id=product.brand_id,
        category_id=product.category_id,
        brand_name=product.brand.name if product.brand else None,
        category_name=product.category.name if product.category else None,
        presentation=product.presentation,
        unit_price=float(product.unit_price),
        wholesale_price=float(product.wholesale_price) if product.wholesale_price is not None else None,
        cost_price=float(product.cost_price) if product.cost_price is not None else None,
        min_stock=product.min_stock,
        comentario=product.comentario,
        total_stock=total_stock,
        on_order_qty=on_order_qty,
        on_order_eta=on_order_eta,
        is_active=product.is_active,
    )


@router.get("/search", response_model=list[ProductSearch])
def search_products(
    q: str = Query("", min_length=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Quick search for POS autocomplete (by code or name, top 20)."""
    query = db.query(Product).filter(Product.is_active == True)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Product.code.ilike(pattern),
                Product.name.ilike(pattern),
            )
        )
    query = query.outerjoin(Brand, Product.brand_id == Brand.id)
    products = query.order_by(Product.name).limit(20).all()
    results = []
    for p in products:
        stock = _get_total_stock(db, p.id)
        on_order_qty, on_order_eta = (None, None)
        if stock <= 0:
            on_order_qty, on_order_eta = _get_pending_order_info(db, p.id)
        results.append(ProductSearch(
            id=p.id,
            code=p.code,
            name=p.name,
            brand_name=p.brand.name if p.brand else None,
            presentation=p.presentation,
            unit_price=float(p.unit_price),
            wholesale_price=float(p.wholesale_price) if p.wholesale_price is not None else None,
            cost_price=float(p.cost_price) if p.cost_price is not None else None,
            stock=stock,
            on_order_qty=on_order_qty,
            on_order_eta=on_order_eta,
        ))
    return results


@router.get("", response_model=list[ProductOut])
def list_products(
    search: str | None = Query(None),
    brand_id: int | None = Query(None),
    category_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = (
        db.query(Product)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .filter(Product.is_active == True)
    )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.code.ilike(pattern),
                Product.name.ilike(pattern),
            )
        )
    if brand_id is not None:
        query = query.filter(Product.brand_id == brand_id)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    products = query.order_by(Product.name).all()
    if not products:
        return []

    product_ids = [p.id for p in products]

    # Batch: get total stock for all products in one query
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

    # Batch: get pending order info for out-of-stock products in one query
    oos_ids = [pid for pid in product_ids if stock_map.get(pid, 0) <= 0]
    order_map: dict[int, tuple[int | None, date | None]] = {}
    if oos_ids:
        order_rows = (
            db.query(
                PurchaseOrderItem.product_id,
                func.coalesce(func.sum(PurchaseOrderItem.quantity), 0).label("qty"),
                func.min(PurchaseOrder.expected_delivery_date).label("eta"),
            )
            .join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
            .filter(
                PurchaseOrderItem.product_id.in_(oos_ids),
                PurchaseOrder.status == "DRAFT",
            )
            .group_by(PurchaseOrderItem.product_id)
            .all()
        )
        for row in order_rows:
            qty = int(row.qty)
            if qty > 0:
                order_map[row.product_id] = (qty, row.eta)

    results = []
    for p in products:
        total_stock = stock_map.get(p.id, 0)
        on_order_qty, on_order_eta = order_map.get(p.id, (None, None))
        results.append(ProductOut(
            id=p.id,
            code=p.code,
            name=p.name,
            brand_id=p.brand_id,
            category_id=p.category_id,
            brand_name=p.brand.name if p.brand else None,
            category_name=p.category.name if p.category else None,
            presentation=p.presentation,
            unit_price=float(p.unit_price),
            wholesale_price=float(p.wholesale_price) if p.wholesale_price is not None else None,
            cost_price=float(p.cost_price) if p.cost_price is not None else None,
            min_stock=p.min_stock,
            comentario=p.comentario,
            total_stock=total_stock,
            on_order_qty=on_order_qty,
            on_order_eta=on_order_eta,
            is_active=p.is_active,
        ))
    return results


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    existing = db.query(Product).filter(Product.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de producto ya existe",
        )
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return _product_to_out(product, db)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return _product_to_out(product, db)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    update_data = data.model_dump(exclude_unset=True)
    if "code" in update_data:
        dup = db.query(Product).filter(Product.code == update_data["code"], Product.id != product_id).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de producto ya existe",
            )
    for key, value in update_data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return _product_to_out(product, db)


@router.delete("/{product_id}", response_model=ProductOut)
def deactivate_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    product.is_active = False
    db.commit()
    db.refresh(product)
    return _product_to_out(product, db)
