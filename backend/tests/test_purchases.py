"""Purchase orders: create → receive → stock update."""


def _make_po_payload(seed):
    return {
        "supplier_id": seed["supplier"].id,
        "warehouse_id": seed["warehouse"].id,
        "items": [{
            "product_id": seed["product"].id,
            "quantity": 20,
            "unit_cost": 60.0,
        }],
    }


def test_create_purchase_order(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/purchase-orders", headers=s["admin_headers"], json=_make_po_payload(s))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "DRAFT"
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 20


def test_receive_purchase_order_adds_stock(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/purchase-orders", headers=s["admin_headers"], json=_make_po_payload(s))
    po_id = r.json()["id"]

    r2 = client.post(f"/api/v1/purchase-orders/{po_id}/receive", headers=s["admin_headers"])
    assert r2.status_code == 200
    assert r2.json()["status"] == "RECEIVED"

    # Stock should be 100 + 20 = 120
    inv = client.get(
        f"/api/v1/inventory?warehouse_id={s['warehouse'].id}",
        headers=s["admin_headers"],
    )
    prod_inv = [i for i in inv.json() if i["product_id"] == s["product"].id]
    assert prod_inv[0]["quantity"] == 120


def test_cannot_receive_twice(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/purchase-orders", headers=s["admin_headers"], json=_make_po_payload(s))
    po_id = r.json()["id"]
    client.post(f"/api/v1/purchase-orders/{po_id}/receive", headers=s["admin_headers"])

    r2 = client.post(f"/api/v1/purchase-orders/{po_id}/receive", headers=s["admin_headers"])
    assert r2.status_code == 400


def test_cancel_purchase_order(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/purchase-orders", headers=s["admin_headers"], json=_make_po_payload(s))
    po_id = r.json()["id"]

    r2 = client.delete(f"/api/v1/purchase-orders/{po_id}", headers=s["admin_headers"])
    assert r2.status_code == 200
    assert r2.json()["status"] == "CANCELLED"


def test_cannot_cancel_received_order(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/purchase-orders", headers=s["admin_headers"], json=_make_po_payload(s))
    po_id = r.json()["id"]
    client.post(f"/api/v1/purchase-orders/{po_id}/receive", headers=s["admin_headers"])

    r2 = client.delete(f"/api/v1/purchase-orders/{po_id}", headers=s["admin_headers"])
    assert r2.status_code == 400
