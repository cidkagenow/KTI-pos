"""
Sales lifecycle tests — the MOST CRITICAL test file.

Covers: preventa → facturar → anular, stock deductions,
        document numbering, IGV math, RUC validation, role restrictions.
"""

from unittest.mock import patch
from decimal import Decimal


def _make_sale_payload(seed):
    """Helper: build a valid SaleCreate dict from seed_all data."""
    return {
        "doc_type": "FACTURA",
        "series": "F001",
        "client_id": seed["ruc_client"].id,
        "warehouse_id": seed["warehouse"].id,
        "seller_id": seed["admin_user"].id,
        "items": [{
            "product_id": seed["product"].id,
            "quantity": 2,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    }


def _make_boleta_payload(seed):
    """Helper: boleta with DNI client."""
    return {
        "doc_type": "BOLETA",
        "series": "B001",
        "client_id": seed["dni_client"].id,
        "warehouse_id": seed["warehouse"].id,
        "seller_id": seed["admin_user"].id,
        "items": [{
            "product_id": seed["product"].id,
            "quantity": 1,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    }


# ── 1. Create preventa → stock deducted ──

def test_create_sale_deducts_stock(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PREVENTA"
    assert body["doc_number"] == 1
    assert len(body["items"]) == 1

    # Stock should go from 100 to 98
    inv = client.get(
        f"/api/v1/inventory?warehouse_id={s['warehouse'].id}",
        headers=s["admin_headers"],
    )
    prod_inv = [i for i in inv.json() if i["product_id"] == s["product"].id]
    assert prod_inv[0]["quantity"] == 98


# ── 2. Facturar → status changes, SUNAT called (mocked) ──

def test_facturar_sale(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    sale_id = r.json()["id"]

    with patch("app.services.sunat_service.send_factura_to_sunat") as mock_sunat, \
         patch("app.services.email_service.send_factura_email"):
        mock_sunat.return_value = {
            "sunat_status": "ACEPTADO",
            "sunat_description": "La Factura fue aceptada",
        }
        r2 = client.post(f"/api/v1/sales/{sale_id}/facturar", headers=s["admin_headers"])

    assert r2.status_code == 200
    assert r2.json()["status"] == "FACTURADO"
    assert r2.json()["sunat_status"] == "ACEPTADO"


# ── 3. Anular → stock returned ──

def test_anular_returns_stock(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    sale_id = r.json()["id"]

    with patch("app.services.sunat_service.send_factura_to_sunat") as mock_sunat, \
         patch("app.services.email_service.send_factura_email"):
        mock_sunat.return_value = {"sunat_status": "ACEPTADO"}
        client.post(f"/api/v1/sales/{sale_id}/facturar", headers=s["admin_headers"])

    r3 = client.post(
        f"/api/v1/sales/{sale_id}/anular",
        headers=s["admin_headers"],
        json={"reason": "Error de digitación"},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "ANULADO"

    # Stock should be back to 100
    inv = client.get(
        f"/api/v1/inventory?warehouse_id={s['warehouse'].id}",
        headers=s["admin_headers"],
    )
    prod_inv = [i for i in inv.json() if i["product_id"] == s["product"].id]
    assert prod_inv[0]["quantity"] == 100


# ── 4. Factura requires RUC client ──

def test_factura_requires_ruc(client, seed_all):
    s = seed_all
    payload = _make_sale_payload(s)
    payload["client_id"] = s["dni_client"].id  # DNI, not RUC
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=payload)
    assert r.status_code == 400
    assert "RUC" in r.json()["detail"]


# ── 5. Cannot facturar already facturado ──

def test_cannot_double_facturar(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    sale_id = r.json()["id"]

    with patch("app.services.sunat_service.send_factura_to_sunat") as m, \
         patch("app.services.email_service.send_factura_email"):
        m.return_value = {"sunat_status": "ACEPTADO"}
        client.post(f"/api/v1/sales/{sale_id}/facturar", headers=s["admin_headers"])

    r2 = client.post(f"/api/v1/sales/{sale_id}/facturar", headers=s["admin_headers"])
    assert r2.status_code == 400


# ── 6. Cannot anular already anulado ──

def test_cannot_double_anular(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    sale_id = r.json()["id"]

    client.post(
        f"/api/v1/sales/{sale_id}/anular",
        headers=s["admin_headers"],
        json={"reason": "First anulación"},
    )
    r2 = client.post(
        f"/api/v1/sales/{sale_id}/anular",
        headers=s["admin_headers"],
        json={"reason": "Second"},
    )
    assert r2.status_code == 400


# ── 7. Delete preventa → stock returned, status ELIMINADO ──

def test_delete_preventa_returns_stock(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    sale_id = r.json()["id"]

    r2 = client.delete(f"/api/v1/sales/{sale_id}", headers=s["admin_headers"])
    assert r2.status_code == 200
    assert r2.json()["status"] == "ELIMINADO"

    # Stock back to 100
    inv = client.get(
        f"/api/v1/inventory?warehouse_id={s['warehouse'].id}",
        headers=s["admin_headers"],
    )
    prod_inv = [i for i in inv.json() if i["product_id"] == s["product"].id]
    assert prod_inv[0]["quantity"] == 100


# ── 8. Document series auto-increments ──

def test_doc_number_auto_increments(client, seed_all):
    s = seed_all
    r1 = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    assert r1.json()["doc_number"] == 1

    r2 = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    assert r2.json()["doc_number"] == 2


# ── 9. IGV calculation ──

def test_igv_calculation(client, seed_all):
    s = seed_all
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json=_make_sale_payload(s))
    body = r.json()
    # 2 units × 100.00 = 200.00 total with IGV
    total = Decimal(str(body["total"]))
    subtotal = Decimal(str(body["subtotal"]))
    igv = Decimal(str(body["igv_amount"]))
    assert total == Decimal("200.00")
    assert subtotal + igv == total
    # subtotal = 200 / 1.18 ≈ 169.49
    assert subtotal == Decimal("169.49")


# ── 10. VENTAS can create but not facturar ──

def test_ventas_can_create_but_not_facturar(client, seed_all):
    s = seed_all
    payload = _make_boleta_payload(s)
    payload["seller_id"] = s["ventas_user"].id
    r = client.post("/api/v1/sales", headers=s["ventas_headers"], json=payload)
    assert r.status_code == 201

    sale_id = r.json()["id"]
    r2 = client.post(f"/api/v1/sales/{sale_id}/facturar", headers=s["ventas_headers"])
    assert r2.status_code == 403
