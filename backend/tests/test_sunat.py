"""SUNAT integration tests with mocked service."""

from datetime import date
from unittest.mock import patch

from app.models.sunat import SunatDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_and_facturar(client, seed, doc_type="FACTURA", series="F001", client_key="ruc_client"):
    """Helper: create a sale and facturar it, returning the sale_id."""
    r = client.post("/api/v1/sales", headers=seed["admin_headers"], json={
        "doc_type": doc_type,
        "series": series,
        "client_id": seed[client_key].id,
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


def _anular_sale(client, seed, sale_id):
    """Helper: anular a sale."""
    client.post(
        f"/api/v1/sales/{sale_id}/anular",
        headers=seed["admin_headers"],
        json={"reason": "Test anulacion"},
    )


# ---------------------------------------------------------------------------
# Factura tests (existing)
# ---------------------------------------------------------------------------

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


def test_reenviar_factura(client, seed_all):
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    # First send returns ERROR
    with patch("app.api.sunat.send_factura_to_sunat") as mock_s, \
         patch("app.api.sunat.send_factura_email"):
        mock_s.return_value = {"sunat_status": "ERROR", "sunat_description": "Timeout"}
        client.post(f"/api/v1/sunat/facturas/{sale_id}/enviar", headers=s["admin_headers"])

    # Reenviar returns ACEPTADO
    with patch("app.api.sunat.send_factura_to_sunat") as mock_s, \
         patch("app.api.sunat.send_factura_email"):
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        r = client.post(f"/api/v1/sunat/facturas/{sale_id}/reenviar", headers=s["admin_headers"])

    assert r.status_code == 200
    assert r.json()["sunat_status"] == "ACEPTADO"
    assert r.json()["attempt_count"] == 3  # facturar(1) + enviar(2) + reenviar(3)


def test_reenviar_already_accepted_fails(client, seed_all):
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    # Send and accept
    with patch("app.api.sunat.send_factura_to_sunat") as mock_s, \
         patch("app.api.sunat.send_factura_email"):
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sunat/facturas/{sale_id}/enviar", headers=s["admin_headers"])

    # Reenviar should fail — already accepted
    with patch("app.api.sunat.send_factura_to_sunat"), \
         patch("app.api.sunat.send_factura_email"):
        r = client.post(f"/api/v1/sunat/facturas/{sale_id}/reenviar", headers=s["admin_headers"])

    assert r.status_code == 400
    assert "ya fue aceptada" in r.json()["detail"]


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


# ---------------------------------------------------------------------------
# Resumen de Boletas tests
# ---------------------------------------------------------------------------

def test_resumen_boletas_sends_pending(client, seed_all):
    """Create a boleta, facturar it, then send resumen for today."""
    s = seed_all
    sale_id = _create_and_facturar(
        client, s, doc_type="BOLETA", series="B001", client_key="dni_client",
    )

    today = date.today().isoformat()

    # Check pending count
    r = client.get(
        f"/api/v1/sunat/resumen-boletas/pendientes?fecha={today}",
        headers=s["admin_headers"],
    )
    assert r.status_code == 200
    assert r.json()["nuevas"] >= 1

    # Send resumen
    with patch("app.api.sunat.send_resumen_to_sunat") as mock_s:
        mock_s.return_value = {
            "sunat_status": "PENDIENTE",
            "sunat_description": "Resumen enviado",
            "ticket": "TICKET-123",
        }
        r = client.post(
            "/api/v1/sunat/resumen-boletas",
            headers=s["admin_headers"],
            json={"fecha": today},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["sunat_status"] == "PENDIENTE"
    assert body["ticket"] == "TICKET-123"
    assert body["doc_category"] == "RESUMEN"


def test_resumen_boletas_no_pending_fails(client, seed_all):
    """If no boletas for that date, should return 400."""
    s = seed_all
    r = client.post(
        "/api/v1/sunat/resumen-boletas",
        headers=s["admin_headers"],
        json={"fecha": "2020-01-01"},
    )
    assert r.status_code == 400
    assert "No hay boletas" in r.json()["detail"]


def test_resumen_boletas_includes_anuladas(client, seed_all):
    """Anuladas boletas that were previously accepted should be in the resumen."""
    s = seed_all
    sale_id = _create_and_facturar(
        client, s, doc_type="BOLETA", series="B001", client_key="dni_client",
    )

    today = date.today().isoformat()

    # First send resumen to mark boleta as ACEPTADO
    with patch("app.api.sunat.send_resumen_to_sunat") as mock_s:
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(
            "/api/v1/sunat/resumen-boletas",
            headers=s["admin_headers"],
            json={"fecha": today},
        )

    # Anular the boleta
    _anular_sale(client, s, sale_id)

    # Now pending should show anuladas
    r = client.get(
        f"/api/v1/sunat/resumen-boletas/pendientes?fecha={today}",
        headers=s["admin_headers"],
    )
    assert r.status_code == 200
    assert r.json()["anuladas"] >= 1

    # Send resumen again (with the anulada)
    with patch("app.api.sunat.send_resumen_to_sunat") as mock_s:
        mock_s.return_value = {
            "sunat_status": "ACEPTADO",
            "sunat_description": "Resumen con anulacion aceptado",
        }
        r = client.post(
            "/api/v1/sunat/resumen-boletas",
            headers=s["admin_headers"],
            json={"fecha": today},
        )

    assert r.status_code == 200
    assert r.json()["sunat_status"] == "ACEPTADO"


def test_resumen_accepted_boletas_not_resent(client, seed_all):
    """Once a boleta resumen is ACEPTADO, those boletas should not appear as pending again."""
    s = seed_all
    _create_and_facturar(
        client, s, doc_type="BOLETA", series="B001", client_key="dni_client",
    )

    today = date.today().isoformat()

    # Send resumen and accept
    with patch("app.api.sunat.send_resumen_to_sunat") as mock_s:
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(
            "/api/v1/sunat/resumen-boletas",
            headers=s["admin_headers"],
            json={"fecha": today},
        )

    # Pending count should be 0 now
    r = client.get(
        f"/api/v1/sunat/resumen-boletas/pendientes?fecha={today}",
        headers=s["admin_headers"],
    )
    assert r.status_code == 200
    assert r.json()["nuevas"] == 0


# ---------------------------------------------------------------------------
# Baja tests
# ---------------------------------------------------------------------------

def test_enviar_baja_requires_anulado(client, seed_all):
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    # Sale is FACTURADO, not ANULADO — baja should fail
    r = client.post("/api/v1/sunat/baja", headers=s["admin_headers"], json={
        "sale_id": sale_id,
        "motivo": "ANULACION",
    })
    assert r.status_code == 400


def test_enviar_baja_success(client, seed_all):
    """Anular a factura, then send baja to SUNAT."""
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    # Send to SUNAT first (so it has an ACEPTADO record)
    with patch("app.api.sunat.send_factura_to_sunat") as mock_s, \
         patch("app.api.sunat.send_factura_email"):
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sunat/facturas/{sale_id}/enviar", headers=s["admin_headers"])

    # Anular the sale
    _anular_sale(client, s, sale_id)

    # Send baja
    with patch("app.api.sunat.send_baja_to_sunat") as mock_s:
        mock_s.return_value = {
            "sunat_status": "PENDIENTE",
            "sunat_description": "Baja enviada",
            "ticket": "BAJA-TICKET-001",
        }
        r = client.post("/api/v1/sunat/baja", headers=s["admin_headers"], json={
            "sale_id": sale_id,
            "motivo": "ANULACION DE OPERACION",
        })

    assert r.status_code == 200
    body = r.json()
    assert body["sunat_status"] == "PENDIENTE"
    assert body["ticket"] == "BAJA-TICKET-001"
    assert body["doc_category"] == "BAJA"


def test_enviar_baja_requires_factura(client, seed_all):
    """Baja only works for facturas, not boletas."""
    s = seed_all
    sale_id = _create_and_facturar(
        client, s, doc_type="BOLETA", series="B001", client_key="dni_client",
    )
    _anular_sale(client, s, sale_id)

    r = client.post("/api/v1/sunat/baja", headers=s["admin_headers"], json={
        "sale_id": sale_id,
        "motivo": "ANULACION",
    })
    assert r.status_code == 400
    assert "boletas" in r.json()["detail"].lower()


def test_enviar_baja_without_prior_sunat_send(client, seed_all, db_session):
    """Baja should work even if factura was never sent to SUNAT."""
    s = seed_all
    sale_id = _create_and_facturar(client, s)
    # Delete the SUNAT document so there's no acceptance record
    db_session.query(SunatDocument).filter(SunatDocument.sale_id == sale_id).delete()
    db_session.commit()

    _anular_sale(client, s, sale_id)

    with patch("app.api.sunat.send_baja_to_sunat") as mock_s:
        mock_s.return_value = {
            "sunat_status": "PENDIENTE",
            "sunat_description": "Baja enviada",
            "ticket": "BAJA-NO-PREV",
        }
        r = client.post("/api/v1/sunat/baja", headers=s["admin_headers"], json={
            "sale_id": sale_id,
            "motivo": "ANULACION DE OPERACION",
        })

    assert r.status_code == 200
    assert r.json()["sunat_status"] == "PENDIENTE"


def test_enviar_baja_duplicate_blocked(client, seed_all):
    """Can't send baja twice for the same sale."""
    s = seed_all
    sale_id = _create_and_facturar(client, s)

    with patch("app.api.sunat.send_factura_to_sunat") as mock_s, \
         patch("app.api.sunat.send_factura_email"):
        mock_s.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        client.post(f"/api/v1/sunat/facturas/{sale_id}/enviar", headers=s["admin_headers"])

    _anular_sale(client, s, sale_id)

    # First baja
    with patch("app.api.sunat.send_baja_to_sunat") as mock_s:
        mock_s.return_value = {"sunat_status": "PENDIENTE", "ticket": "T1"}
        client.post("/api/v1/sunat/baja", headers=s["admin_headers"], json={
            "sale_id": sale_id, "motivo": "ANULACION",
        })

    # Second baja should be blocked
    r = client.post("/api/v1/sunat/baja", headers=s["admin_headers"], json={
        "sale_id": sale_id,
        "motivo": "ANULACION",
    })
    assert r.status_code == 400
    assert "Ya se envio baja" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Ticket status check
# ---------------------------------------------------------------------------

def test_check_ticket_status(client, seed_all):
    """Send resumen with PENDIENTE ticket, then check ticket resolves to ACEPTADO."""
    s = seed_all
    _create_and_facturar(
        client, s, doc_type="BOLETA", series="B001", client_key="dni_client",
    )

    today = date.today().isoformat()

    # Send resumen → PENDIENTE with ticket
    with patch("app.api.sunat.send_resumen_to_sunat") as mock_s:
        mock_s.return_value = {
            "sunat_status": "PENDIENTE",
            "sunat_description": "En proceso",
            "ticket": "TICKET-456",
        }
        client.post(
            "/api/v1/sunat/resumen-boletas",
            headers=s["admin_headers"],
            json={"fecha": today},
        )

    # Check ticket → resolves to ACEPTADO
    with patch("app.api.sunat.check_ticket_status") as mock_t:
        mock_t.return_value = {
            "sunat_status": "ACEPTADO",
            "sunat_description": "Resumen aceptado por SUNAT",
        }
        r = client.post(
            "/api/v1/sunat/ticket/TICKET-456/status",
            headers=s["admin_headers"],
        )

    assert r.status_code == 200
    assert r.json()["sunat_status"] == "ACEPTADO"


def test_check_ticket_still_processing(client, seed_all):
    """If SUNAT says still processing, status should remain PENDIENTE."""
    s = seed_all
    _create_and_facturar(
        client, s, doc_type="BOLETA", series="B001", client_key="dni_client",
    )

    today = date.today().isoformat()

    with patch("app.api.sunat.send_resumen_to_sunat") as mock_s:
        mock_s.return_value = {
            "sunat_status": "PENDIENTE",
            "sunat_description": "En proceso",
            "ticket": "TICKET-789",
        }
        client.post(
            "/api/v1/sunat/resumen-boletas",
            headers=s["admin_headers"],
            json={"fecha": today},
        )

    # Check ticket → still processing
    with patch("app.api.sunat.check_ticket_status") as mock_t:
        mock_t.return_value = {"processing": True}
        r = client.post(
            "/api/v1/sunat/ticket/TICKET-789/status",
            headers=s["admin_headers"],
        )

    assert r.status_code == 200
    assert r.json()["sunat_status"] == "PENDIENTE"
