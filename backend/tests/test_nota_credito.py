"""
Nota de Crédito tests — full lifecycle.

Covers: NC creation from FACTURADO sale, item validation, motivo codes,
        stock return for motivos 01/04, no stock return for 02/03/06,
        facturar NC (SUNAT mocked), document numbering, role restrictions,
        SUNAT NC endpoint.
"""

from unittest.mock import patch
from decimal import Decimal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_and_facturar(client, seed, qty=2):
    """Create a factura sale and facturar it. Returns the sale dict."""
    r = client.post("/api/v1/sales", headers=seed["admin_headers"], json={
        "doc_type": "FACTURA",
        "series": "F001",
        "client_id": seed["ruc_client"].id,
        "warehouse_id": seed["warehouse"].id,
        "seller_id": seed["admin_user"].id,
        "items": [{
            "product_id": seed["product"].id,
            "quantity": qty,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    })
    assert r.status_code == 201
    sale_id = r.json()["id"]

    with patch("app.services.sunat_service.send_factura_to_sunat") as mock_s, \
         patch("app.services.email_service.send_factura_email"):
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        r2 = client.post(f"/api/v1/sales/{sale_id}/facturar", headers=seed["admin_headers"])

    assert r2.status_code == 200
    return r2.json()


def _make_nc_payload(ref_sale_id, product_id, qty=1, motivo="04"):
    """Build a NotaCreditoCreate dict."""
    motivo_texts = {
        "01": "Anulacion de la operacion",
        "02": "Correccion por error en la descripcion",
        "03": "Descuento global",
        "04": "Devolucion total o parcial",
        "06": "Ajuste de precio",
    }
    return {
        "ref_sale_id": ref_sale_id,
        "nc_motivo_code": motivo,
        "nc_motivo_text": motivo_texts.get(motivo, "Test"),
        "items": [{
            "product_id": product_id,
            "quantity": qty,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    }


def _get_stock(client, seed):
    """Return current stock for the seed product in the seed warehouse."""
    inv = client.get(
        f"/api/v1/inventory?warehouse_id={seed['warehouse'].id}",
        headers=seed["admin_headers"],
    )
    prod_inv = [i for i in inv.json() if i["product_id"] == seed["product"].id]
    return prod_inv[0]["quantity"] if prod_inv else 0


# ---------------------------------------------------------------------------
# 1. Create NC from FACTURADO sale
# ---------------------------------------------------------------------------

def test_create_nota_credito(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)
    payload = _make_nc_payload(sale["id"], s["product"].id, qty=1)

    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    assert r.status_code == 201
    nc = r.json()
    assert nc["doc_type"] == "NOTA_CREDITO"
    assert nc["series"] == "FN01"
    assert nc["doc_number"] == 1
    assert nc["status"] == "PREVENTA"
    assert nc["ref_sale_id"] == sale["id"]
    assert nc["nc_motivo_code"] == "04"
    assert nc["nc_motivo_text"] == "Devolucion total o parcial"
    assert len(nc["items"]) == 1
    assert nc["items"][0]["quantity"] == 1


# ---------------------------------------------------------------------------
# 2. NC doc number auto-increments
# ---------------------------------------------------------------------------

def test_nc_doc_number_increments(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s, qty=5)

    r1 = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"],
                      json=_make_nc_payload(sale["id"], s["product"].id, qty=1))
    assert r1.json()["doc_number"] == 1

    r2 = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"],
                      json=_make_nc_payload(sale["id"], s["product"].id, qty=1))
    assert r2.json()["doc_number"] == 2


# ---------------------------------------------------------------------------
# 3. Cannot create NC from non-FACTURADO sale
# ---------------------------------------------------------------------------

def test_nc_requires_facturado_sale(client, seed_all):
    s = seed_all
    # Create a PREVENTA sale (not facturado)
    r = client.post("/api/v1/sales", headers=s["admin_headers"], json={
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
    preventa_id = r.json()["id"]

    payload = _make_nc_payload(preventa_id, s["product"].id)
    r2 = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    assert r2.status_code == 400
    assert "FACTURADAS" in r2.json()["detail"]


# ---------------------------------------------------------------------------
# 4. NC items must be subset of original — bad product rejected
# ---------------------------------------------------------------------------

def test_nc_rejects_product_not_in_original(client, seed_all, db_session):
    s = seed_all
    sale = _create_and_facturar(client, s)

    # Create a second product that is NOT in the original sale
    from app.models.product import Product
    from app.models.inventory import Inventory
    p2 = Product(code="PROD002", name="Otro Producto", brand_id=s["brand"].id,
                 unit_price=Decimal("50.00"), min_stock=1)
    db_session.add(p2)
    db_session.flush()
    db_session.add(Inventory(product_id=p2.id, warehouse_id=s["warehouse"].id, quantity=50))
    db_session.commit()

    payload = _make_nc_payload(sale["id"], p2.id, qty=1)
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    assert r.status_code == 400
    assert "no existe en la venta original" in r.json()["detail"]


# ---------------------------------------------------------------------------
# 5. NC quantity cannot exceed original
# ---------------------------------------------------------------------------

def test_nc_rejects_quantity_exceeding_original(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s, qty=2)

    payload = _make_nc_payload(sale["id"], s["product"].id, qty=5)  # original had 2
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    assert r.status_code == 400
    assert "excede" in r.json()["detail"]


# ---------------------------------------------------------------------------
# 6. NC must have at least one item
# ---------------------------------------------------------------------------

def test_nc_requires_items(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    payload = {
        "ref_sale_id": sale["id"],
        "nc_motivo_code": "04",
        "nc_motivo_text": "Devolucion",
        "items": [],
    }
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    assert r.status_code == 400
    assert "al menos un item" in r.json()["detail"]


# ---------------------------------------------------------------------------
# 7. Facturar NC with motivo 04 (devolucion) → stock returned
# ---------------------------------------------------------------------------

def test_facturar_nc_devolucion_returns_stock(client, seed_all):
    s = seed_all
    stock_before = _get_stock(client, s)  # 100
    sale = _create_and_facturar(client, s, qty=5)
    stock_after_sale = _get_stock(client, s)  # 95
    assert stock_after_sale == stock_before - 5

    # Create NC for 3 items with motivo 04 (devolucion)
    payload = _make_nc_payload(sale["id"], s["product"].id, qty=3, motivo="04")
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]
    # NC creation does NOT change stock
    assert _get_stock(client, s) == stock_after_sale

    # Facturar NC → stock should return
    with patch("app.services.sunat_service.send_nota_credito_to_sunat") as mock_nc:
        mock_nc.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "NC aceptada"}
        r2 = client.post(f"/api/v1/sales/{nc_id}/facturar", headers=s["admin_headers"])

    assert r2.status_code == 200
    assert r2.json()["status"] == "FACTURADO"
    assert r2.json()["sunat_status"] == "ACEPTADO"
    # Stock should be 95 + 3 = 98
    assert _get_stock(client, s) == stock_after_sale + 3


# ---------------------------------------------------------------------------
# 8. Facturar NC with motivo 01 (anulacion) → stock returned
# ---------------------------------------------------------------------------

def test_facturar_nc_anulacion_returns_stock(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s, qty=2)
    stock_after_sale = _get_stock(client, s)  # 98

    payload = _make_nc_payload(sale["id"], s["product"].id, qty=2, motivo="01")
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]

    with patch("app.services.sunat_service.send_nota_credito_to_sunat") as mock_nc:
        mock_nc.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sales/{nc_id}/facturar", headers=s["admin_headers"])

    assert _get_stock(client, s) == stock_after_sale + 2  # 100


# ---------------------------------------------------------------------------
# 9. Facturar NC with motivo 03 (descuento) → stock NOT returned
# ---------------------------------------------------------------------------

def test_facturar_nc_descuento_no_stock_return(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s, qty=2)
    stock_after_sale = _get_stock(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id, qty=2, motivo="03")
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]

    with patch("app.services.sunat_service.send_nota_credito_to_sunat") as mock_nc:
        mock_nc.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sales/{nc_id}/facturar", headers=s["admin_headers"])

    # Stock unchanged — descuento doesn't return stock
    assert _get_stock(client, s) == stock_after_sale


# ---------------------------------------------------------------------------
# 10. Facturar NC with motivo 02 (correccion) → stock NOT returned
# ---------------------------------------------------------------------------

def test_facturar_nc_correccion_no_stock_return(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s, qty=2)
    stock_after_sale = _get_stock(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id, qty=1, motivo="02")
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]

    with patch("app.services.sunat_service.send_nota_credito_to_sunat") as mock_nc:
        mock_nc.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sales/{nc_id}/facturar", headers=s["admin_headers"])

    assert _get_stock(client, s) == stock_after_sale


# ---------------------------------------------------------------------------
# 11. Facturar NC with motivo 06 (ajuste precio) → stock NOT returned
# ---------------------------------------------------------------------------

def test_facturar_nc_ajuste_precio_no_stock_return(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s, qty=2)
    stock_after_sale = _get_stock(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id, qty=1, motivo="06")
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]

    with patch("app.services.sunat_service.send_nota_credito_to_sunat") as mock_nc:
        mock_nc.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sales/{nc_id}/facturar", headers=s["admin_headers"])

    assert _get_stock(client, s) == stock_after_sale


# ---------------------------------------------------------------------------
# 12. VENTAS role cannot create NC (admin only)
# ---------------------------------------------------------------------------

def test_ventas_cannot_create_nc(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id)
    r = client.post("/api/v1/sales/nota-credito", headers=s["ventas_headers"], json=payload)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# 13. NC totals / IGV calculation
# ---------------------------------------------------------------------------

def test_nc_igv_calculation(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s, qty=3)

    payload = _make_nc_payload(sale["id"], s["product"].id, qty=2)
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc = r.json()

    # 2 units × 100.00 = 200.00 total with IGV
    total = Decimal(str(nc["total"]))
    subtotal = Decimal(str(nc["subtotal"]))
    igv = Decimal(str(nc["igv_amount"]))
    assert total == Decimal("200.00")
    assert subtotal + igv == total
    assert subtotal == Decimal("169.49")


# ---------------------------------------------------------------------------
# 14. NC appears in sales list with correct doc_type
# ---------------------------------------------------------------------------

def test_nc_appears_in_sales_list(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id)
    client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)

    r = client.get("/api/v1/sales?doc_type=NOTA_CREDITO", headers=s["admin_headers"])
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 1
    assert data[0]["doc_type"] == "NOTA_CREDITO"
    assert data[0]["ref_sale_id"] == sale["id"]
    assert data[0]["nc_motivo_code"] == "04"


# ---------------------------------------------------------------------------
# 15. NC ref_sale_id is included in GET /sales/{id}
# ---------------------------------------------------------------------------

def test_nc_detail_includes_ref_fields(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id, motivo="01")
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]

    r2 = client.get(f"/api/v1/sales/{nc_id}", headers=s["admin_headers"])
    assert r2.status_code == 200
    nc = r2.json()
    assert nc["ref_sale_id"] == sale["id"]
    assert nc["nc_motivo_code"] == "01"
    assert nc["nc_motivo_text"] == "Anulacion de la operacion"


# ---------------------------------------------------------------------------
# 16. SUNAT enviar NC endpoint
# ---------------------------------------------------------------------------

def test_sunat_enviar_nota_credito(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id)
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]

    # Facturar the NC first
    with patch("app.services.sunat_service.send_nota_credito_to_sunat") as mock_nc:
        mock_nc.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sales/{nc_id}/facturar", headers=s["admin_headers"])

    # Now send via SUNAT endpoint
    with patch("app.api.sunat.send_nota_credito_to_sunat") as mock_nc:
        mock_nc.return_value = {
            "sunat_status": "ACEPTADO",
            "sunat_description": "NC aceptada por SUNAT",
            "sunat_hash": "nc_hash_123",
        }
        r2 = client.post(
            f"/api/v1/sunat/nota-credito/{nc_id}/enviar",
            headers=s["admin_headers"],
        )

    assert r2.status_code == 200
    assert r2.json()["sunat_status"] == "ACEPTADO"
    assert r2.json()["doc_category"] == "NOTA_CREDITO"


# ---------------------------------------------------------------------------
# 17. SUNAT enviar NC — rejects non-NC sale
# ---------------------------------------------------------------------------

def test_sunat_enviar_nc_rejects_factura(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    r = client.post(
        f"/api/v1/sunat/nota-credito/{sale['id']}/enviar",
        headers=s["admin_headers"],
    )
    assert r.status_code == 400
    assert "no es una nota de credito" in r.json()["detail"]


# ---------------------------------------------------------------------------
# 18. SUNAT enviar NC — requires FACTURADO status
# ---------------------------------------------------------------------------

def test_sunat_enviar_nc_requires_facturado(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id)
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc_id = r.json()["id"]
    # NC is in PREVENTA — not facturado yet

    r2 = client.post(
        f"/api/v1/sunat/nota-credito/{nc_id}/enviar",
        headers=s["admin_headers"],
    )
    assert r2.status_code == 400
    assert "FACTURADA" in r2.json()["detail"]


# ---------------------------------------------------------------------------
# 19. NC without active series fails with clear message
# ---------------------------------------------------------------------------

def test_nc_fails_without_series(client, seed_all, db_session):
    s = seed_all
    sale = _create_and_facturar(client, s)

    # Deactivate ALL NC series
    from app.models.sale import DocumentSeries
    nc_all = db_session.query(DocumentSeries).filter(
        DocumentSeries.doc_type == "NOTA_CREDITO"
    ).all()
    for nc_s in nc_all:
        nc_s.is_active = False
    db_session.commit()

    payload = _make_nc_payload(sale["id"], s["product"].id)
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    assert r.status_code == 400
    assert "serie" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 20. NC inherits client/warehouse from original sale
# ---------------------------------------------------------------------------

def test_nc_inherits_client_warehouse(client, seed_all):
    s = seed_all
    sale = _create_and_facturar(client, s)

    payload = _make_nc_payload(sale["id"], s["product"].id)
    r = client.post("/api/v1/sales/nota-credito", headers=s["admin_headers"], json=payload)
    nc = r.json()

    assert nc["client_id"] == sale["client_id"]
    assert nc["client_name"] == sale["client_name"]
    assert nc["warehouse_id"] == sale["warehouse_id"]
