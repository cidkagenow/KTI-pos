"""SUNAT integration tests with mocked service."""

from unittest.mock import patch


def _create_and_facturar(client, seed):
    """Helper: create a sale and facturar it, returning the sale_id."""
    r = client.post("/api/v1/sales", headers=seed["admin_headers"], json={
        "doc_type": "FACTURA",
        "series": "F001",
        "client_id": seed["ruc_client"].id,
        "warehouse_id": seed["warehouse"].id,
        "seller_id": seed["admin_user"].id,
        "items": [{
            "product_id": seed["product"].id,
            "quantity": 1,
            "unit_price": 100.0,
            "discount_pct": 0,
        }],
    })
    sale_id = r.json()["id"]

    with patch("app.services.sunat_service.send_factura_to_sunat") as mock_s, \
         patch("app.services.email_service.send_factura_email"):
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sales/{sale_id}/facturar", headers=seed["admin_headers"])

    return sale_id


def test_enviar_factura(client, seed_all):
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    with patch("app.api.sunat.send_factura_to_sunat") as mock_s, \
         patch("app.api.sunat.send_factura_email"):
        mock_s.return_value = {
            "sunat_status": "ACEPTADO",
            "sunat_description": "La Factura fue aceptada",
            "sunat_hash": "abc123",
        }
        r = client.post(
            f"/api/v1/sunat/facturas/{sale_id}/enviar",
            headers=s["admin_headers"],
        )

    assert r.status_code == 200
    assert r.json()["sunat_status"] == "ACEPTADO"


def test_list_sunat_documents(client, seed_all):
    s = seed_all
    _create_and_facturar(client, s)

    r = client.get("/api/v1/sunat/documentos", headers=s["admin_headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1


def test_sunat_sale_status(client, seed_all):
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    r = client.get(f"/api/v1/sunat/documentos/sale/{sale_id}", headers=s["admin_headers"])
    assert r.status_code == 200
    assert r.json()["sunat_status"] == "ACEPTADO"


def test_enviar_baja_requires_anulado(client, seed_all):
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    # Sale is FACTURADO, not ANULADO — baja should fail
    r = client.post("/api/v1/sunat/baja", headers=s["admin_headers"], json={
        "sale_id": sale_id,
        "motivo": "ANULACION",
    })
    assert r.status_code == 400
