"""Dashboard & report endpoint tests."""

from datetime import date


def test_dashboard_empty(client, admin_user, admin_headers):
    r = client.get("/api/v1/reports/dashboard", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["today_sales"] == 0
    assert body["today_total"] == 0
    assert body["low_stock_count"] == 0


def test_dashboard_with_sale(client, seed_all):
    s = seed_all
    # Create a sale so dashboard counts it
    client.post("/api/v1/sales", headers=s["admin_headers"], json={
        "doc_type": "FACTURA",
        "series": "F001",
        "client_id": s["ruc_client"].id,
        "warehouse_id": s["warehouse"].id,
        "seller_id": s["admin_user"].id,
        "items": [{
            "product_id": s["product"].id,
            "quantity": 1,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    })
    r = client.get("/api/v1/reports/dashboard", headers=s["admin_headers"])
    body = r.json()
    assert body["today_sales"] >= 1
    assert body["today_total"] > 0


def test_top_products(client, seed_all):
    s = seed_all
    today = date.today().isoformat()
    client.post("/api/v1/sales", headers=s["admin_headers"], json={
        "doc_type": "FACTURA",
        "series": "F001",
        "client_id": s["ruc_client"].id,
        "warehouse_id": s["warehouse"].id,
        "seller_id": s["admin_user"].id,
        "items": [{
            "product_id": s["product"].id,
            "quantity": 5,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    })
    r = client.get(
        f"/api/v1/reports/top-products?from_date={today}&to_date={today}",
        headers=s["admin_headers"],
    )
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    assert results[0]["quantity_sold"] == 5


def test_profit_report(client, seed_all):
    s = seed_all
    today = date.today().isoformat()
    client.post("/api/v1/sales", headers=s["admin_headers"], json={
        "doc_type": "FACTURA",
        "series": "F001",
        "client_id": s["ruc_client"].id,
        "warehouse_id": s["warehouse"].id,
        "seller_id": s["admin_user"].id,
        "items": [{
            "product_id": s["product"].id,
            "quantity": 3,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    })
    r = client.get(
        f"/api/v1/reports/profit-report?from_date={today}&to_date={today}",
        headers=s["admin_headers"],
    )
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    assert results[0]["total_cost"] > 0
    assert results[0]["profit"] > 0


def test_dashboard_low_stock(client, seed_all, db_session):
    """Low stock shows in dashboard when qty <= min_stock."""
    from app.models.inventory import Inventory

    s = seed_all
    inv = db_session.query(Inventory).filter(
        Inventory.product_id == s["product"].id,
    ).first()
    inv.quantity = 2  # below min_stock of 5
    db_session.commit()

    r = client.get("/api/v1/reports/dashboard", headers=s["admin_headers"])
    assert r.json()["low_stock_count"] >= 1
