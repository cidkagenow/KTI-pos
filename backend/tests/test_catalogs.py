"""Brands, categories, warehouses, document series, suppliers."""


# ── Brands ──

def test_create_brand(client, admin_user, admin_headers):
    r = client.post("/api/v1/catalogs/brands", headers=admin_headers, json={"name": "Samsung"})
    assert r.status_code == 201
    assert r.json()["name"] == "Samsung"


def test_create_brand_duplicate(client, admin_user, admin_headers, seed_brand):
    r = client.post("/api/v1/catalogs/brands", headers=admin_headers, json={"name": "TestBrand"})
    assert r.status_code == 400


def test_list_brands(client, admin_user, admin_headers, seed_brand):
    r = client.get("/api/v1/catalogs/brands", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ── Categories ──

def test_create_category(client, admin_user, admin_headers):
    r = client.post("/api/v1/catalogs/categories", headers=admin_headers, json={"name": "Electrónica"})
    assert r.status_code == 201


def test_list_categories(client, admin_user, admin_headers, seed_category):
    r = client.get("/api/v1/catalogs/categories", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ── Warehouses ──

def test_create_warehouse(client, admin_user, admin_headers):
    r = client.post("/api/v1/catalogs/warehouses", headers=admin_headers, json={
        "name": "Almacén Nuevo",
        "address": "Calle 1",
    })
    assert r.status_code == 201
    assert r.json()["name"] == "Almacén Nuevo"


# ── Document Series ──

def test_create_document_series(client, admin_user, admin_headers):
    r = client.post("/api/v1/catalogs/document-series", headers=admin_headers, json={
        "doc_type": "FACTURA",
        "series": "F002",
    })
    assert r.status_code == 201
    assert r.json()["next_number"] == 1


# ── Suppliers ──

def test_create_supplier(client, admin_user, admin_headers):
    r = client.post("/api/v1/catalogs/suppliers", headers=admin_headers, json={
        "ruc": "20111222333",
        "business_name": "Nuevo Proveedor",
        "city": "Cusco",
    })
    assert r.status_code == 201
    assert r.json()["business_name"] == "Nuevo Proveedor"
