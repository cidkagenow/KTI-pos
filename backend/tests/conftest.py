"""
Shared fixtures for the KTI-POS test suite.

Uses SQLite in-memory DB — each test function gets a clean database.
External services (SUNAT, Gemini) are mocked at the service level.
"""

import pytest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.utils.security import hash_password, create_access_token

# Import ALL models so Base.metadata knows every table
from app.models.user import User
from app.models.client import Client
from app.models.product import Product, Brand, Category
from app.models.warehouse import Warehouse
from app.models.sale import Sale, SaleItem, DocumentSeries
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.inventory import Inventory, InventoryMovement
from app.models.sunat import SunatDocument
from app.models.chat import ChatMessage


# ---------------------------------------------------------------------------
# Database engine & session (SQLite in-memory, per-test)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # single connection shared — critical for in-memory
    )

    # SQLite needs foreign-key enforcement turned on explicitly.
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI TestClient (overrides get_db)
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_user(db_session):
    user = User(
        username="admin_test",
        password_hash=hash_password("admin123"),
        full_name="Admin Test",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def ventas_user(db_session):
    user = User(
        username="ventas_test",
        password_hash=hash_password("ventas123"),
        full_name="Ventas Test",
        role="VENTAS",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Auth headers (JWT tokens)
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_headers(admin_user):
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def ventas_headers(ventas_user):
    token = create_access_token({"sub": str(ventas_user.id)})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Catalog seed data
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_brand(db_session):
    brand = Brand(name="TestBrand")
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)
    return brand


@pytest.fixture()
def seed_category(db_session):
    cat = Category(name="TestCategory")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture()
def seed_warehouse(db_session):
    wh = Warehouse(name="Almacén Principal", address="Lima")
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh


@pytest.fixture()
def seed_warehouse_b(db_session):
    wh = Warehouse(name="Almacén Secundario", address="Arequipa")
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh


@pytest.fixture()
def seed_product(db_session, seed_brand, seed_category):
    p = Product(
        code="PROD001",
        name="Producto Test",
        brand_id=seed_brand.id,
        category_id=seed_category.id,
        unit_price=Decimal("100.00"),
        wholesale_price=Decimal("90.00"),
        cost_price=Decimal("60.00"),
        min_stock=5,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture()
def seed_product_with_stock(db_session, seed_product, seed_warehouse):
    inv = Inventory(
        product_id=seed_product.id,
        warehouse_id=seed_warehouse.id,
        quantity=100,
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    return seed_product


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_ruc_client(db_session):
    c = Client(
        doc_type="RUC",
        doc_number="20525996957",
        business_name="Empresa Test SAC",
        address="Av. Test 123",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture()
def seed_dni_client(db_session):
    c = Client(
        doc_type="DNI",
        doc_number="12345678",
        business_name="Juan Pérez",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Document Series
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_doc_series_factura(db_session):
    ds = DocumentSeries(doc_type="FACTURA", series="F001", next_number=1)
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    return ds


@pytest.fixture()
def seed_doc_series_boleta(db_session):
    ds = DocumentSeries(doc_type="BOLETA", series="B001", next_number=1)
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    return ds


@pytest.fixture()
def seed_doc_series_nc(db_session):
    """NC series for FACTURA (starts with F) and BOLETA (starts with B)."""
    ds_f = DocumentSeries(doc_type="NOTA_CREDITO", series="FN01", next_number=1)
    ds_b = DocumentSeries(doc_type="NOTA_CREDITO", series="BN01", next_number=1)
    db_session.add_all([ds_f, ds_b])
    db_session.commit()
    db_session.refresh(ds_f)
    return ds_f


@pytest.fixture()
def seed_doc_series_nv(db_session):
    ds = DocumentSeries(doc_type="NOTA_VENTA", series="NV01", next_number=1)
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    return ds


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_supplier(db_session):
    s = Supplier(
        ruc="20123456789",
        business_name="Proveedor Test",
        city="Lima",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


# ---------------------------------------------------------------------------
# Composite "seed everything" fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_all(
    admin_user,
    ventas_user,
    admin_headers,
    ventas_headers,
    seed_brand,
    seed_category,
    seed_warehouse,
    seed_warehouse_b,
    seed_product_with_stock,
    seed_ruc_client,
    seed_dni_client,
    seed_doc_series_factura,
    seed_doc_series_boleta,
    seed_doc_series_nc,
    seed_doc_series_nv,
    seed_supplier,
):
    return {
        "admin_user": admin_user,
        "ventas_user": ventas_user,
        "admin_headers": admin_headers,
        "ventas_headers": ventas_headers,
        "brand": seed_brand,
        "category": seed_category,
        "warehouse": seed_warehouse,
        "warehouse_b": seed_warehouse_b,
        "product": seed_product_with_stock,
        "ruc_client": seed_ruc_client,
        "dni_client": seed_dni_client,
        "doc_series_factura": seed_doc_series_factura,
        "doc_series_boleta": seed_doc_series_boleta,
        "doc_series_nc": seed_doc_series_nc,
        "doc_series_nv": seed_doc_series_nv,
        "supplier": seed_supplier,
    }
