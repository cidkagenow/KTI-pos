from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Brand, Category
from app.models.warehouse import Warehouse
from app.models.sale import DocumentSeries
from app.models.purchase import Supplier
from app.models.user import User
from app.schemas.product import BrandOut, BrandCreate, CategoryOut, CategoryCreate
from app.schemas.sale import DocumentSeriesOut, DocumentSeriesCreate
from app.schemas.purchase import SupplierOut, SupplierCreate
from app.api.deps import get_current_user, require_admin

router = APIRouter()


# --------------- Brands ---------------

@router.get("/brands", response_model=list[BrandOut])
def list_brands(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    brands = db.query(Brand).filter(Brand.is_active == True).order_by(Brand.name).all()
    return [BrandOut.model_validate(b) for b in brands]


@router.post("/brands", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
def create_brand(
    data: BrandCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    existing = db.query(Brand).filter(Brand.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La marca ya existe",
        )
    brand = Brand(name=data.name)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return BrandOut.model_validate(brand)


@router.get("/brands/{brand_id}", response_model=BrandOut)
def get_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )
    return BrandOut.model_validate(brand)


@router.put("/brands/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: int,
    data: BrandCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )
    dup = db.query(Brand).filter(Brand.name == data.name, Brand.id != brand_id).first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La marca ya existe",
        )
    brand.name = data.name
    db.commit()
    db.refresh(brand)
    return BrandOut.model_validate(brand)


@router.delete("/brands/{brand_id}", response_model=BrandOut)
def deactivate_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )
    brand.is_active = False
    db.commit()
    db.refresh(brand)
    return BrandOut.model_validate(brand)


# --------------- Categories ---------------

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cats = db.query(Category).filter(Category.is_active == True).order_by(Category.name).all()
    return [CategoryOut.model_validate(c) for c in cats]


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    existing = db.query(Category).filter(Category.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La categoría ya existe",
        )
    cat = Category(name=data.name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )
    return CategoryOut.model_validate(cat)


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )
    dup = db.query(Category).filter(Category.name == data.name, Category.id != category_id).first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La categoría ya existe",
        )
    cat.name = data.name
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.delete("/categories/{category_id}", response_model=CategoryOut)
def deactivate_category(
    category_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )
    cat.is_active = False
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat)


# --------------- Warehouses ---------------

class WarehouseOut(BrandOut):
    """Reuse same shape: id + name."""
    pass


class WarehouseCreate(BrandCreate):
    address: str | None = None


class WarehouseUpdate(BrandCreate):
    address: str | None = None


@router.get("/warehouses", response_model=list[dict])
def list_warehouses(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    warehouses = db.query(Warehouse).filter(Warehouse.is_active == True).order_by(Warehouse.name).all()
    return [
        {"id": w.id, "name": w.name, "address": w.address, "is_active": w.is_active}
        for w in warehouses
    ]


@router.post("/warehouses", status_code=status.HTTP_201_CREATED)
def create_warehouse(
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    existing = db.query(Warehouse).filter(Warehouse.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El almacén ya existe",
        )
    warehouse = Warehouse(name=data.name, address=data.address)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return {"id": warehouse.id, "name": warehouse.name, "address": warehouse.address, "is_active": warehouse.is_active}


@router.get("/warehouses/{warehouse_id}")
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    w = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if w is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén no encontrado",
        )
    return {"id": w.id, "name": w.name, "address": w.address, "is_active": w.is_active}


@router.put("/warehouses/{warehouse_id}")
def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    w = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if w is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén no encontrado",
        )
    dup = db.query(Warehouse).filter(Warehouse.name == data.name, Warehouse.id != warehouse_id).first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El almacén ya existe",
        )
    w.name = data.name
    if data.address is not None:
        w.address = data.address
    db.commit()
    db.refresh(w)
    return {"id": w.id, "name": w.name, "address": w.address, "is_active": w.is_active}


@router.delete("/warehouses/{warehouse_id}")
def deactivate_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    w = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if w is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén no encontrado",
        )
    w.is_active = False
    db.commit()
    db.refresh(w)
    return {"id": w.id, "name": w.name, "address": w.address, "is_active": w.is_active}


# --------------- Document Series ---------------

@router.get("/document-series", response_model=list[DocumentSeriesOut])
def list_document_series(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    series = db.query(DocumentSeries).order_by(DocumentSeries.doc_type, DocumentSeries.series).all()
    return [DocumentSeriesOut.model_validate(s) for s in series]


@router.post("/document-series", response_model=DocumentSeriesOut, status_code=status.HTTP_201_CREATED)
def create_document_series(
    data: DocumentSeriesCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    existing = (
        db.query(DocumentSeries)
        .filter(DocumentSeries.doc_type == data.doc_type, DocumentSeries.series == data.series)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La serie ya existe para este tipo de documento",
        )
    ds = DocumentSeries(doc_type=data.doc_type, series=data.series)
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return DocumentSeriesOut.model_validate(ds)


@router.put("/document-series/{series_id}", response_model=DocumentSeriesOut)
def update_document_series(
    series_id: int,
    data: DocumentSeriesCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    ds = db.query(DocumentSeries).filter(DocumentSeries.id == series_id).first()
    if ds is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serie no encontrada",
        )
    ds.doc_type = data.doc_type
    ds.series = data.series
    db.commit()
    db.refresh(ds)
    return DocumentSeriesOut.model_validate(ds)


@router.post("/document-series/{series_id}/set-default", response_model=DocumentSeriesOut)
def set_default_series(
    series_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """Set a series as default for its doc_type. Unsets other defaults of same type."""
    ds = db.query(DocumentSeries).filter(DocumentSeries.id == series_id).first()
    if ds is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serie no encontrada",
        )
    # Unset all other defaults for this doc_type
    db.query(DocumentSeries).filter(
        DocumentSeries.doc_type == ds.doc_type,
        DocumentSeries.id != series_id,
    ).update({"is_default": False})
    ds.is_default = True
    db.commit()
    db.refresh(ds)
    return DocumentSeriesOut.model_validate(ds)


# --------------- Suppliers ---------------

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return [SupplierOut.model_validate(s) for s in db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.business_name).all()]


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    s = Supplier(
        ruc=data.ruc,
        business_name=data.business_name,
        city=data.city,
        phone=data.phone,
        email=data.email,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return SupplierOut.model_validate(s)


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: int,
    data: SupplierCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    s.business_name = data.business_name
    if data.ruc is not None:
        s.ruc = data.ruc
    if data.city is not None:
        s.city = data.city
    if data.phone is not None:
        s.phone = data.phone
    if data.email is not None:
        s.email = data.email
    db.commit()
    db.refresh(s)
    return SupplierOut.model_validate(s)


@router.delete("/suppliers/{supplier_id}")
def deactivate_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    s.is_active = False
    db.commit()
    return {"ok": True}
