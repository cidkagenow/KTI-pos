"""
Comprehensive chatbot tool-function tests.

Tests the ACTUAL database queries the chatbot executes when users ask questions.
Each tool function is tested directly with real seed data — no Gemini mocking.
This catches bugs like wrong queries, missing joins, or broken filters.
"""

import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.services.gemini_service import (
    _exec_search_products,
    _exec_get_product_details,
    _exec_check_inventory,
    _exec_search_clients,
    _exec_get_client_details,
    _exec_get_sales_summary,
    _exec_search_sales,
)
from app.models.product import Product, Brand, Category
from app.models.client import Client
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.models.sale import Sale, SaleItem, DocumentSeries
from app.models.user import User
from app.utils.security import hash_password


# ─── Fixture: rich seed data for chatbot queries ────────────────────────────

@pytest.fixture()
def chat_data(db_session):
    """Seed the DB with realistic data for chatbot tool testing."""
    # Users
    admin = User(
        username="admin", password_hash=hash_password("x"),
        full_name="Carlos Admin", role="ADMIN",
    )
    seller = User(
        username="maria", password_hash=hash_password("x"),
        full_name="María Vendedora", role="VENTAS",
    )
    db_session.add_all([admin, seller])
    db_session.flush()

    # Brands & Categories
    duro = Brand(name="DURO")
    pirelli = Brand(name="PIRELLI")
    llantas = Category(name="Llantas")
    aceites = Category(name="Aceites")
    db_session.add_all([duro, pirelli, llantas, aceites])
    db_session.flush()

    # Warehouses
    wh_main = Warehouse(name="Almacén Principal", address="Lima")
    wh_sec = Warehouse(name="Almacén Secundario", address="Arequipa")
    db_session.add_all([wh_main, wh_sec])
    db_session.flush()

    # Products
    p1 = Product(
        code="LLA-001", name="Llanta 195/65R15",
        brand_id=duro.id, category_id=llantas.id,
        unit_price=Decimal("250.00"), wholesale_price=Decimal("230.00"),
        cost_price=Decimal("180.00"), min_stock=10,
    )
    p2 = Product(
        code="LLA-002", name="Llanta 205/55R16",
        brand_id=pirelli.id, category_id=llantas.id,
        unit_price=Decimal("350.00"), wholesale_price=Decimal("320.00"),
        cost_price=Decimal("260.00"), min_stock=5,
    )
    p3 = Product(
        code="ACE-001", name="Aceite Motor 5W-30",
        brand_id=None, category_id=aceites.id,
        unit_price=Decimal("45.00"), cost_price=Decimal("30.00"),
        min_stock=20,
    )
    p4 = Product(
        code="LLA-003", name="Llanta 175/70R13",
        brand_id=duro.id, category_id=llantas.id,
        unit_price=Decimal("180.00"), cost_price=Decimal("120.00"),
        min_stock=8, is_active=False,  # inactive product
    )
    db_session.add_all([p1, p2, p3, p4])
    db_session.flush()

    # Inventory
    db_session.add_all([
        Inventory(product_id=p1.id, warehouse_id=wh_main.id, quantity=25),
        Inventory(product_id=p1.id, warehouse_id=wh_sec.id, quantity=10),
        Inventory(product_id=p2.id, warehouse_id=wh_main.id, quantity=3),   # below min_stock=5
        Inventory(product_id=p3.id, warehouse_id=wh_main.id, quantity=50),
    ])
    db_session.flush()

    # Clients
    c1 = Client(
        doc_type="RUC", doc_number="20525996957",
        business_name="Transportes Lima SAC", address="Av. Colonial 456",
        zona="Lima Norte", phone="999888777",
    )
    c2 = Client(
        doc_type="DNI", doc_number="12345678",
        business_name="Juan Pérez", phone="987654321",
    )
    c3 = Client(
        doc_type="RUC", doc_number="20111222333",
        business_name="Distribuidora Arequipa", zona="Arequipa",
    )
    db_session.add_all([c1, c2, c3])
    db_session.flush()

    # Document series
    ds = DocumentSeries(doc_type="FACTURA", series="F001", next_number=1)
    db_session.add(ds)
    db_session.flush()

    # Sales (2 sales today, different sellers)
    sale1 = Sale(
        doc_type="FACTURA", series="F001", doc_number=1,
        client_id=c1.id, warehouse_id=wh_main.id,
        seller_id=admin.id, created_by=admin.id,
        subtotal=Decimal("423.73"), igv_amount=Decimal("76.27"),
        total=Decimal("500.00"), status="FACTURADO",
        issue_date=date.today(),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(sale1)
    db_session.flush()

    si1 = SaleItem(
        sale_id=sale1.id, product_id=p1.id, quantity=2,
        unit_price=Decimal("250.00"), discount_pct=Decimal("0"),
        line_total=Decimal("500.00"),
        product_code="LLA-001", product_name="Llanta 195/65R15",
        brand_name="DURO",
    )
    db_session.add(si1)

    sale2 = Sale(
        doc_type="FACTURA", series="F001", doc_number=2,
        client_id=c2.id, warehouse_id=wh_main.id,
        seller_id=seller.id, created_by=seller.id,
        subtotal=Decimal("38.14"), igv_amount=Decimal("6.86"),
        total=Decimal("45.00"), status="PREVENTA",
        issue_date=date.today(),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(sale2)
    db_session.flush()

    si2 = SaleItem(
        sale_id=sale2.id, product_id=p3.id, quantity=1,
        unit_price=Decimal("45.00"), discount_pct=Decimal("0"),
        line_total=Decimal("45.00"),
        product_code="ACE-001", product_name="Aceite Motor 5W-30",
    )
    db_session.add(si2)

    # Anulled sale (should be excluded from summaries)
    sale3 = Sale(
        doc_type="FACTURA", series="F001", doc_number=3,
        client_id=c1.id, warehouse_id=wh_main.id,
        seller_id=admin.id, created_by=admin.id,
        subtotal=Decimal("84.75"), igv_amount=Decimal("15.25"),
        total=Decimal("100.00"), status="ANULADA",
        issue_date=date.today(),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(sale3)
    db_session.commit()

    return {
        "admin": admin, "seller": seller,
        "p1": p1, "p2": p2, "p3": p3, "p4": p4,
        "wh_main": wh_main, "wh_sec": wh_sec,
        "c1": c1, "c2": c2, "c3": c3,
        "sale1": sale1, "sale2": sale2, "sale3": sale3,
        "duro": duro, "pirelli": pirelli,
        "llantas": llantas, "aceites": aceites,
    }


# ═══════════════════════════════════════════════════════════════════════════
# search_products — "buscar llanta", "tienes aceite?", "productos duro"
# ═══════════════════════════════════════════════════════════════════════════

class TestSearchProducts:
    """User asks: 'buscar llanta', 'tienes aceite?', 'productos marca duro'"""

    def test_search_by_name(self, db_session, chat_data):
        """'buscar llanta' → finds llantas"""
        result = json.loads(_exec_search_products(db_session, {"query": "llanta"}, "ADMIN"))
        assert len(result) == 2  # p1 and p2 (p4 is inactive)
        names = [r["name"] for r in result]
        assert "Llanta 195/65R15" in names
        assert "Llanta 205/55R16" in names

    def test_search_by_code(self, db_session, chat_data):
        """'buscar ACE-001' → finds aceite"""
        result = json.loads(_exec_search_products(db_session, {"query": "ACE-001"}, "ADMIN"))
        assert len(result) == 1
        assert result[0]["code"] == "ACE-001"

    def test_search_by_brand_name_in_query(self, db_session, chat_data):
        """'buscar duro' → finds products with brand DURO"""
        result = json.loads(_exec_search_products(db_session, {"query": "duro"}, "ADMIN"))
        assert len(result) >= 1
        assert all(r["brand"] == "DURO" for r in result)

    def test_search_by_brand_filter(self, db_session, chat_data):
        """'productos marca PIRELLI' → brand filter"""
        result = json.loads(_exec_search_products(db_session, {"brand": "PIRELLI"}, "ADMIN"))
        assert len(result) == 1
        assert result[0]["brand"] == "PIRELLI"

    def test_search_by_category(self, db_session, chat_data):
        """'productos categoría aceites' → category filter"""
        result = json.loads(_exec_search_products(db_session, {"category": "aceites"}, "ADMIN"))
        assert len(result) == 1
        assert result[0]["name"] == "Aceite Motor 5W-30"

    def test_search_brand_plus_query(self, db_session, chat_data):
        """'llanta duro' → query=llanta + brand=duro"""
        result = json.loads(_exec_search_products(
            db_session, {"query": "llanta", "brand": "duro"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["brand"] == "DURO"
        assert "Llanta" in result[0]["name"]

    def test_search_multi_word_fallback(self, db_session, chat_data):
        """'llanta duro' as single query → fallback splits words"""
        result = json.loads(_exec_search_products(
            db_session, {"query": "llanta duro"}, "ADMIN"
        ))
        assert len(result) >= 1  # fallback should find DURO brand products

    def test_search_no_results(self, db_session, chat_data):
        """'buscar xyz123' → empty list"""
        result = json.loads(_exec_search_products(db_session, {"query": "xyz123"}, "ADMIN"))
        assert result == []

    def test_excludes_inactive_products(self, db_session, chat_data):
        """Inactive product LLA-003 should not appear"""
        result = json.loads(_exec_search_products(db_session, {"query": "175/70"}, "ADMIN"))
        assert len(result) == 0

    def test_includes_stock(self, db_session, chat_data):
        """Results include total stock"""
        result = json.loads(_exec_search_products(db_session, {"query": "LLA-001"}, "ADMIN"))
        assert result[0]["stock_total"] == 35  # 25 main + 10 sec

    def test_admin_sees_cost_price(self, db_session, chat_data):
        """ADMIN role sees cost_price"""
        result = json.loads(_exec_search_products(db_session, {"query": "LLA-001"}, "ADMIN"))
        assert "cost_price" in result[0]
        assert result[0]["cost_price"] == "180.00"

    def test_ventas_no_cost_price(self, db_session, chat_data):
        """VENTAS role does NOT see cost_price"""
        result = json.loads(_exec_search_products(db_session, {"query": "LLA-001"}, "VENTAS"))
        assert "cost_price" not in result[0]

    def test_limit_works(self, db_session, chat_data):
        """Limit caps results"""
        result = json.loads(_exec_search_products(db_session, {"query": "llanta", "limit": 1}, "ADMIN"))
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════
# get_product_details — "info del producto X", "detalle LLA-001"
# ═══════════════════════════════════════════════════════════════════════════

class TestGetProductDetails:
    """User asks: 'detalle del producto 1', 'cuánto cuesta la llanta?'"""

    def test_returns_full_details(self, db_session, chat_data):
        result = json.loads(_exec_get_product_details(
            db_session, {"product_id": chat_data["p1"].id}, "ADMIN"
        ))
        assert result["code"] == "LLA-001"
        assert result["name"] == "Llanta 195/65R15"
        assert result["brand"] == "DURO"
        assert result["category"] == "Llantas"
        assert result["unit_price"] == "250.00"
        assert result["wholesale_price"] == "230.00"
        assert result["min_stock"] == 10

    def test_stock_by_warehouse(self, db_session, chat_data):
        """Shows stock per warehouse"""
        result = json.loads(_exec_get_product_details(
            db_session, {"product_id": chat_data["p1"].id}, "ADMIN"
        ))
        stock = result["stock_by_warehouse"]
        assert len(stock) == 2
        warehouses = {s["warehouse"]: s["quantity"] for s in stock}
        assert warehouses["Almacén Principal"] == 25
        assert warehouses["Almacén Secundario"] == 10

    def test_admin_sees_cost(self, db_session, chat_data):
        result = json.loads(_exec_get_product_details(
            db_session, {"product_id": chat_data["p1"].id}, "ADMIN"
        ))
        assert result["cost_price"] == "180.00"

    def test_ventas_no_cost(self, db_session, chat_data):
        result = json.loads(_exec_get_product_details(
            db_session, {"product_id": chat_data["p1"].id}, "VENTAS"
        ))
        assert "cost_price" not in result

    def test_nonexistent_product(self, db_session, chat_data):
        result = json.loads(_exec_get_product_details(
            db_session, {"product_id": 9999}, "ADMIN"
        ))
        assert "error" in result

    def test_inactive_product_not_found(self, db_session, chat_data):
        """Inactive products should not be returned"""
        result = json.loads(_exec_get_product_details(
            db_session, {"product_id": chat_data["p4"].id}, "ADMIN"
        ))
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# check_inventory — "cuánto stock hay?", "productos con stock bajo"
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckInventory:
    """User asks: 'stock de llantas', 'hay stock bajo?', 'stock en almacén principal'"""

    def test_all_inventory(self, db_session, chat_data):
        result = json.loads(_exec_check_inventory(db_session, {}, "ADMIN"))
        assert len(result) >= 3  # p1 main, p1 sec, p2 main, p3 main

    def test_filter_by_product_name(self, db_session, chat_data):
        """'stock de aceite' → only aceite"""
        result = json.loads(_exec_check_inventory(
            db_session, {"product_name": "aceite"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["product"] == "Aceite Motor 5W-30"
        assert result[0]["quantity"] == 50

    def test_filter_by_warehouse(self, db_session, chat_data):
        """'stock en almacén secundario'"""
        result = json.loads(_exec_check_inventory(
            db_session, {"warehouse_name": "Secundario"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["warehouse"] == "Almacén Secundario"
        assert result[0]["quantity"] == 10

    def test_low_stock_only(self, db_session, chat_data):
        """'productos con stock bajo' → p2 has 3 < min_stock 5"""
        result = json.loads(_exec_check_inventory(
            db_session, {"low_stock_only": True}, "ADMIN"
        ))
        assert len(result) >= 1
        low_codes = [r["product_code"] for r in result]
        assert "LLA-002" in low_codes
        assert all(r["is_low"] for r in result)

    def test_low_stock_flag(self, db_session, chat_data):
        """Products with stock >= min_stock have is_low=False"""
        result = json.loads(_exec_check_inventory(
            db_session, {"product_name": "Aceite"}, "ADMIN"
        ))
        assert result[0]["is_low"] is False  # 50 >= 20


# ═══════════════════════════════════════════════════════════════════════════
# search_clients — "buscar cliente Transportes", "cliente con RUC 205..."
# ═══════════════════════════════════════════════════════════════════════════

class TestSearchClients:
    """User asks: 'buscar cliente Lima', 'cliente con DNI 12345678'"""

    def test_search_by_name(self, db_session, chat_data):
        result = json.loads(_exec_search_clients(
            db_session, {"query": "Transportes"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["business_name"] == "Transportes Lima SAC"

    def test_search_by_doc_number(self, db_session, chat_data):
        result = json.loads(_exec_search_clients(
            db_session, {"query": "12345678"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["business_name"] == "Juan Pérez"

    def test_search_by_ruc(self, db_session, chat_data):
        result = json.loads(_exec_search_clients(
            db_session, {"query": "20525996957"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["doc_type"] == "RUC"

    def test_search_partial_name(self, db_session, chat_data):
        """'buscar distribu' → finds Distribuidora Arequipa"""
        result = json.loads(_exec_search_clients(
            db_session, {"query": "distribu"}, "ADMIN"
        ))
        assert len(result) == 1
        assert "Arequipa" in result[0]["business_name"]

    def test_search_no_results(self, db_session, chat_data):
        result = json.loads(_exec_search_clients(
            db_session, {"query": "ClienteInexistente"}, "ADMIN"
        ))
        assert result == []

    def test_includes_contact_info(self, db_session, chat_data):
        result = json.loads(_exec_search_clients(
            db_session, {"query": "Transportes"}, "ADMIN"
        ))
        assert result[0]["phone"] == "999888777"
        assert result[0]["zona"] == "Lima Norte"


# ═══════════════════════════════════════════════════════════════════════════
# get_client_details — "info del cliente X"
# ═══════════════════════════════════════════════════════════════════════════

class TestGetClientDetails:
    """User asks: 'detalle del cliente 1', 'info de Transportes Lima'"""

    def test_returns_full_details(self, db_session, chat_data):
        result = json.loads(_exec_get_client_details(
            db_session, {"client_id": chat_data["c1"].id}, "ADMIN"
        ))
        assert result["business_name"] == "Transportes Lima SAC"
        assert result["doc_type"] == "RUC"
        assert result["doc_number"] == "20525996957"
        assert result["address"] == "Av. Colonial 456"
        assert result["zona"] == "Lima Norte"
        assert result["phone"] == "999888777"

    def test_nonexistent_client(self, db_session, chat_data):
        result = json.loads(_exec_get_client_details(
            db_session, {"client_id": 9999}, "ADMIN"
        ))
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════
# get_sales_summary — "cuánto vendimos hoy?", "ventas del mes"
# ═══════════════════════════════════════════════════════════════════════════

class TestGetSalesSummary:
    """User asks: 'cuánto vendimos hoy?', 'ventas del mes', 'ventas de María'"""

    def test_today_summary(self, db_session, chat_data):
        result = json.loads(_exec_get_sales_summary(
            db_session, {"period": "today"}, "ADMIN"
        ))
        # sale1 (500) + sale2 (45) = 545, sale3 is ANULADA (excluded)
        assert result["sale_count"] == 2
        assert result["total_revenue"] == "545.00"

    def test_month_summary(self, db_session, chat_data):
        result = json.loads(_exec_get_sales_summary(
            db_session, {"period": "month"}, "ADMIN"
        ))
        assert result["sale_count"] >= 2

    def test_excludes_anulada(self, db_session, chat_data):
        """ANULADA sales should NOT be counted"""
        result = json.loads(_exec_get_sales_summary(
            db_session, {"period": "today"}, "ADMIN"
        ))
        # 2 active sales, not 3
        assert result["sale_count"] == 2

    def test_filter_by_seller(self, db_session, chat_data):
        """'ventas de María' → only María's sales"""
        result = json.loads(_exec_get_sales_summary(
            db_session, {"period": "today", "seller_name": "María"}, "ADMIN"
        ))
        assert result["sale_count"] == 1
        assert result["total_revenue"] == "45.00"

    def test_admin_sees_profit(self, db_session, chat_data):
        """ADMIN gets estimated_profit field"""
        result = json.loads(_exec_get_sales_summary(
            db_session, {"period": "today"}, "ADMIN"
        ))
        assert "estimated_profit" in result

    def test_ventas_no_profit(self, db_session, chat_data):
        """VENTAS does NOT get estimated_profit"""
        result = json.loads(_exec_get_sales_summary(
            db_session, {"period": "today"}, "VENTAS"
        ))
        assert "estimated_profit" not in result


# ═══════════════════════════════════════════════════════════════════════════
# search_sales — "últimas ventas", "ventas a Transportes Lima"
# ═══════════════════════════════════════════════════════════════════════════

class TestSearchSales:
    """User asks: 'últimas ventas', 'ventas a Transportes', 'ventas de llanta'"""

    def test_recent_sales(self, db_session, chat_data):
        result = json.loads(_exec_search_sales(db_session, {}, "ADMIN"))
        # Excludes ANULADA, so should be 2
        assert len(result) == 2

    def test_filter_by_client(self, db_session, chat_data):
        """'ventas a Transportes Lima'"""
        result = json.loads(_exec_search_sales(
            db_session, {"client_name": "Transportes"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["client"] == "Transportes Lima SAC"
        assert result[0]["total"] == "500.00"

    def test_filter_by_product(self, db_session, chat_data):
        """'ventas de aceite'"""
        result = json.loads(_exec_search_sales(
            db_session, {"product_name": "Aceite"}, "ADMIN"
        ))
        assert len(result) == 1
        assert result[0]["total"] == "45.00"

    def test_filter_by_date(self, db_session, chat_data):
        today = date.today().isoformat()
        result = json.loads(_exec_search_sales(
            db_session, {"from_date": today, "to_date": today}, "ADMIN"
        ))
        assert len(result) >= 1

    def test_excludes_anulada(self, db_session, chat_data):
        """ANULADA sales excluded from search"""
        result = json.loads(_exec_search_sales(db_session, {}, "ADMIN"))
        statuses = [r["status"] for r in result]
        assert "ANULADA" not in statuses

    def test_includes_doc_format(self, db_session, chat_data):
        """Doc shows formatted as 'FACTURA F001-1'"""
        result = json.loads(_exec_search_sales(
            db_session, {"client_name": "Transportes"}, "ADMIN"
        ))
        assert result[0]["doc"] == "FACTURA F001-1"

    def test_includes_seller_name(self, db_session, chat_data):
        result = json.loads(_exec_search_sales(
            db_session, {"client_name": "Transportes"}, "ADMIN"
        ))
        assert result[0]["seller"] == "Carlos Admin"
