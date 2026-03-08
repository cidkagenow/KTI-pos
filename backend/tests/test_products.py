"""Product CRUD + search + stock tests."""


def test_create_product(client, admin_headers, seed_brand, seed_category, admin_user):
    r = client.post("/api/v1/products", headers=admin_headers, json={
        "code": "NEW001",
        "name": "Producto Nuevo",
        "brand_id": seed_brand.id,
        "category_id": seed_category.id,
        "unit_price": 50.0,
    })
    assert r.status_code == 201
    body = r.json()
    assert body["code"] == "NEW001"
    assert body["total_stock"] == 0


def test_create_product_duplicate_code(client, admin_headers, seed_product_with_stock, admin_user):
    r = client.post("/api/v1/products", headers=admin_headers, json={
        "code": "PROD001",
        "name": "Duplicate",
        "unit_price": 10.0,
    })
    assert r.status_code == 400


def test_list_products(client, admin_headers, seed_product_with_stock, admin_user):
    r = client.get("/api/v1/products", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_search_products(client, admin_headers, seed_product_with_stock, admin_user):
    r = client.get("/api/v1/products/search?q=PROD001", headers=admin_headers)
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    assert results[0]["code"] == "PROD001"
    assert results[0]["stock"] == 100


def test_product_shows_stock(client, admin_headers, seed_product_with_stock, admin_user):
    r = client.get(f"/api/v1/products/{seed_product_with_stock.id}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_stock"] == 100
