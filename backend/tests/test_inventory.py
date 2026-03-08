"""Inventory: adjust, transfer, alerts, movements."""

from app.models.inventory import Inventory


def test_list_inventory(client, admin_headers, seed_product_with_stock, admin_user):
    r = client.get("/api/v1/inventory", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_adjust_stock(client, admin_headers, seed_product_with_stock, seed_warehouse, admin_user):
    r = client.post("/api/v1/inventory/adjust", headers=admin_headers, json={
        "product_id": seed_product_with_stock.id,
        "warehouse_id": seed_warehouse.id,
        "new_quantity": 50,
        "notes": "Ajuste por conteo",
    })
    assert r.status_code == 200
    assert r.json()["quantity"] == 50


def test_adjust_creates_movement(client, admin_headers, seed_product_with_stock, seed_warehouse, admin_user):
    client.post("/api/v1/inventory/adjust", headers=admin_headers, json={
        "product_id": seed_product_with_stock.id,
        "warehouse_id": seed_warehouse.id,
        "new_quantity": 75,
    })
    r = client.get(
        f"/api/v1/inventory/movements?product_id={seed_product_with_stock.id}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    movements = r.json()
    assert len(movements) >= 1
    assert movements[0]["movement_type"] == "ADJUSTMENT"


def test_transfer_stock(
    client, admin_headers, seed_product_with_stock, seed_warehouse, seed_warehouse_b, admin_user,
):
    r = client.post("/api/v1/inventory/transfer", headers=admin_headers, json={
        "product_id": seed_product_with_stock.id,
        "from_warehouse_id": seed_warehouse.id,
        "to_warehouse_id": seed_warehouse_b.id,
        "quantity": 30,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["from"]["quantity"] == 70
    assert body["to"]["quantity"] == 30


def test_transfer_insufficient_stock(
    client, admin_headers, seed_product_with_stock, seed_warehouse, seed_warehouse_b, admin_user,
):
    r = client.post("/api/v1/inventory/transfer", headers=admin_headers, json={
        "product_id": seed_product_with_stock.id,
        "from_warehouse_id": seed_warehouse.id,
        "to_warehouse_id": seed_warehouse_b.id,
        "quantity": 999,
    })
    assert r.status_code == 400


def test_transfer_same_warehouse_error(
    client, admin_headers, seed_product_with_stock, seed_warehouse, admin_user,
):
    r = client.post("/api/v1/inventory/transfer", headers=admin_headers, json={
        "product_id": seed_product_with_stock.id,
        "from_warehouse_id": seed_warehouse.id,
        "to_warehouse_id": seed_warehouse.id,
        "quantity": 10,
    })
    assert r.status_code == 400


def test_low_stock_alerts(client, admin_headers, db_session, seed_product_with_stock, seed_warehouse, admin_user):
    # Set stock below min_stock (5)
    inv = db_session.query(Inventory).filter(
        Inventory.product_id == seed_product_with_stock.id,
    ).first()
    inv.quantity = 3
    db_session.commit()

    r = client.get("/api/v1/inventory/alerts", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["quantity"] == 3


def test_adjust_requires_admin(client, ventas_headers, seed_product_with_stock, seed_warehouse, ventas_user):
    r = client.post("/api/v1/inventory/adjust", headers=ventas_headers, json={
        "product_id": seed_product_with_stock.id,
        "warehouse_id": seed_warehouse.id,
        "new_quantity": 10,
    })
    assert r.status_code == 403
