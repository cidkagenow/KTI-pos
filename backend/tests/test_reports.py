"""Report endpoint tests — ensures correct handling of all document types.

SALE DOCUMENT STATE MACHINE
============================

  doc_type = FACTURA | BOLETA | NOTA_VENTA | NOTA_CREDITO

  ┌───────────┐                     ┌────────────┐
  │ PREVENTA  │──── facturar ──────►│ FACTURADO  │
  │  (draft)  │                     │ (invoiced) │
  └─────┬─────┘                     └──────┬─────┘
        │                                  │
        │ anular                           │ anular
        ▼                                  ▼
  ┌───────────┐                     ┌────────────┐
  │  ANULADO  │                     │  ANULADO   │
  └─────┬─────┘                     └────────────┘
        │ delete (preventa only)
        ▼
  ┌───────────┐
  │ ELIMINADO │
  └───────────┘

REPORT INCLUSION RULES
=======================
  Status filter : PREVENTA or FACTURADO only
  NOTA_VENTA   : ALWAYS excluded (regardless of status)
  NOTA_CREDITO : INCLUDED but amounts SUBTRACTED (negative contribution)
  ANULADO      : excluded (not in SALE_STATUSES)
  ELIMINADO    : excluded (not in SALE_STATUSES)

  Example:
    FACTURA  F001  total=500  (FACTURADO)  → +500
    NC       FN01  total=200  (FACTURADO)  → -200
    ──────────────────────────────────────
    Net revenue reported                   = 300
    Sale count                             = 1 (NC not counted)
"""

from datetime import date
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers — create & facturar sales / NCs via the API
# ---------------------------------------------------------------------------

def _sale_payload(seed, *, qty=5, unit_price=100.0, doc_type="FACTURA",
                  series="F001", client_key="ruc_client"):
    return {
        "doc_type": doc_type,
        "series": series,
        "client_id": seed[client_key].id,
        "warehouse_id": seed["warehouse"].id,
        "seller_id": seed["admin_user"].id,
        "items": [{
            "product_id": seed["product"].id,
            "quantity": qty,
            "unit_price": unit_price,
            "discount_pct": 0,
        }],
    }


def _create_sale(client, seed, **kw):
    """Create a sale (PREVENTA). Returns response dict."""
    r = client.post("/api/v1/sales", headers=seed["admin_headers"],
                    json=_sale_payload(seed, **kw))
    assert r.status_code == 201, r.text
    return r.json()


def _facturar(client, seed, sale_id):
    """Facturar a sale (mock SUNAT). Returns response dict."""
    with patch("app.services.sunat_service.send_factura_to_sunat") as m, \
         patch("app.services.email_service.send_factura_email"):
        m.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        r = client.post(f"/api/v1/sales/{sale_id}/facturar",
                        headers=seed["admin_headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _create_and_facturar(client, seed, **kw):
    """Shortcut: create + facturar. Returns facturado sale dict."""
    sale = _create_sale(client, seed, **kw)
    return _facturar(client, seed, sale["id"])


def _nc_payload(ref_sale_id, product_id, qty=2, unit_price=100.0):
    return {
        "ref_sale_id": ref_sale_id,
        "nc_motivo_code": "04",
        "nc_motivo_text": "Devolucion total o parcial",
        "items": [{
            "product_id": product_id,
            "quantity": qty,
            "unit_price": unit_price,
            "discount_pct": 0,
        }],
    }


def _create_nc(client, seed, ref_sale_id, *, qty=2, unit_price=100.0):
    """Create a Nota de Credito (PREVENTA). Returns response dict."""
    payload = _nc_payload(ref_sale_id, seed["product"].id, qty, unit_price)
    r = client.post("/api/v1/sales/nota-credito",
                    headers=seed["admin_headers"], json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _facturar_nc(client, seed, nc_id):
    """Facturar a Nota de Credito (mock SUNAT). Returns response dict."""
    with patch("app.services.sunat_service.send_nota_credito_to_sunat") as m:
        m.return_value = {"sunat_status": "ACEPTADO", "sunat_description": "OK"}
        r = client.post(f"/api/v1/sales/{nc_id}/facturar",
                        headers=seed["admin_headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _anular(client, seed, sale_id):
    """Anular a sale. Returns response dict."""
    r = client.post(f"/api/v1/sales/{sale_id}/anular",
                    headers=seed["admin_headers"],
                    json={"reason": "Test anulacion"})
    assert r.status_code == 200, r.text
    return r.json()


def _get_dashboard(client, seed):
    r = client.get("/api/v1/reports/dashboard", headers=seed["admin_headers"])
    assert r.status_code == 200
    return r.json()


def _get_top_products(client, seed):
    today = date.today().isoformat()
    r = client.get(
        f"/api/v1/reports/top-products?from_date={today}&to_date={today}",
        headers=seed["admin_headers"],
    )
    assert r.status_code == 200
    return r.json()


def _get_profit_report(client, seed):
    today = date.today().isoformat()
    r = client.get(
        f"/api/v1/reports/profit-report?from_date={today}&to_date={today}",
        headers=seed["admin_headers"],
    )
    assert r.status_code == 200
    return r.json()


# ===================================================================
# DASHBOARD
# ===================================================================

class TestDashboard:
    """Dashboard: today_sales (count), today_total (revenue)."""

    def test_empty(self, client, admin_user, admin_headers):
        r = client.get("/api/v1/reports/dashboard", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["today_sales"] == 0
        assert body["today_total"] == 0
        assert body["low_stock_count"] == 0

    def test_single_sale(self, client, seed_all):
        """One FACTURA → count=1, total=line_total."""
        s = seed_all
        _create_sale(client, s, qty=5, unit_price=100.0)

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1
        assert dash["today_total"] == 500.0

    def test_nc_subtracts_from_total(self, client, seed_all):
        """Sale 500 + NC 200 → count=1, total=300."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=2, unit_price=100.0)

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1   # NC excluded from count
        assert dash["today_total"] == 300.0  # 500 - 200

    def test_nc_partial_return(self, client, seed_all):
        """Sale 500, NC for 1 unit (100) → total=400."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=1, unit_price=100.0)

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1
        assert dash["today_total"] == 400.0

    def test_nc_full_reversal(self, client, seed_all):
        """Sale 500, NC for all 5 units (500) → total=0."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=5, unit_price=100.0)

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1
        assert dash["today_total"] == 0.0

    def test_facturado_nc_also_subtracts(self, client, seed_all):
        """NC facturado still subtracts (same SALE_STATUSES filter)."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        nc = _create_nc(client, s, sale["id"], qty=2, unit_price=100.0)
        _facturar_nc(client, s, nc["id"])

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1
        assert dash["today_total"] == 300.0

    def test_nota_venta_excluded(self, client, seed_all):
        """NOTA_VENTA is never counted in reports."""
        s = seed_all
        _create_sale(client, s, doc_type="NOTA_VENTA", series="NV01",
                     client_key="dni_client", qty=5, unit_price=100.0)

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 0
        assert dash["today_total"] == 0.0

    def test_nota_venta_excluded_alongside_real_sale(self, client, seed_all):
        """NOTA_VENTA doesn't contaminate totals of real sales."""
        s = seed_all
        # Real sale
        _create_sale(client, s, qty=3, unit_price=100.0)
        # Nota de venta (should be invisible)
        _create_sale(client, s, doc_type="NOTA_VENTA", series="NV01",
                     client_key="dni_client", qty=10, unit_price=100.0)

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1
        assert dash["today_total"] == 300.0

    def test_anulado_sale_excluded(self, client, seed_all):
        """Anulado PREVENTA → excluded from reports."""
        s = seed_all
        sale = _create_sale(client, s, qty=5, unit_price=100.0)
        _anular(client, s, sale["id"])

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 0
        assert dash["today_total"] == 0.0

    def test_anulado_facturado_excluded(self, client, seed_all):
        """Facturado then anulado → excluded from reports."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _anular(client, s, sale["id"])

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 0
        assert dash["today_total"] == 0.0

    def test_multiple_ncs_against_same_sale(self, client, seed_all):
        """Two partial NCs both subtract. Sale 500, NC1 100, NC2 200 → 200."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=1, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=2, unit_price=100.0)

        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1
        assert dash["today_total"] == 200.0  # 500 - 100 - 200

    def test_low_stock(self, client, seed_all, db_session):
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


# ===================================================================
# TOP PRODUCTS
# ===================================================================

class TestTopProducts:
    """Top products: quantity_sold and total_revenue per product."""

    def test_basic(self, client, seed_all):
        s = seed_all
        _create_sale(client, s, qty=5, unit_price=100.0)

        results = _get_top_products(client, s)
        assert len(results) >= 1
        assert results[0]["quantity_sold"] == 5
        assert results[0]["total_revenue"] == 500.0

    def test_nc_subtracts_quantity_and_revenue(self, client, seed_all):
        """Sale 5×100, NC 2×100 → qty=3, revenue=300."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=2, unit_price=100.0)

        results = _get_top_products(client, s)
        assert len(results) == 1
        assert results[0]["quantity_sold"] == 3
        assert results[0]["total_revenue"] == 300.0

    def test_nc_full_reversal_zeroes_product(self, client, seed_all):
        """Sale 5×100, NC 5×100 → qty=0, revenue=0."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=5, unit_price=100.0)

        results = _get_top_products(client, s)
        if len(results) > 0:
            assert results[0]["quantity_sold"] == 0
            assert results[0]["total_revenue"] == 0.0

    def test_excludes_nota_venta(self, client, seed_all):
        """NOTA_VENTA products don't appear in top products."""
        s = seed_all
        _create_sale(client, s, doc_type="NOTA_VENTA", series="NV01",
                     client_key="dni_client", qty=10, unit_price=100.0)

        results = _get_top_products(client, s)
        assert len(results) == 0

    def test_excludes_anulado(self, client, seed_all):
        """Anulado sale products don't appear."""
        s = seed_all
        sale = _create_sale(client, s, qty=5, unit_price=100.0)
        _anular(client, s, sale["id"])

        results = _get_top_products(client, s)
        assert len(results) == 0

    def test_multiple_ncs(self, client, seed_all):
        """Sale 5×100, NC1 1×100, NC2 2×100 → qty=2, revenue=200."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=1, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=2, unit_price=100.0)

        results = _get_top_products(client, s)
        assert len(results) == 1
        assert results[0]["quantity_sold"] == 2
        assert results[0]["total_revenue"] == 200.0


# ===================================================================
# PROFIT REPORT (Reporte de Utilidades)
# ===================================================================

class TestProfitReport:
    """Profit report: revenue, cost, profit, margin per product.

    Seed product: cost_price=60.00, unit_price=100.00
    """

    def test_basic_profit(self, client, seed_all):
        """3×100 sale → revenue=300, cost=180, profit=120."""
        s = seed_all
        _create_sale(client, s, qty=3, unit_price=100.0)

        results = _get_profit_report(client, s)
        assert len(results) >= 1
        r = results[0]
        assert r["quantity_sold"] == 3
        assert r["total_revenue"] == 300.0
        assert r["total_cost"] == 180.0   # 3 × 60
        assert r["profit"] == 120.0       # 300 - 180
        assert r["profit_margin"] > 0

    def test_nc_reduces_profit(self, client, seed_all):
        """Sale 5×100, NC 2×100 → net qty=3, revenue=300, cost=180, profit=120."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=2, unit_price=100.0)

        results = _get_profit_report(client, s)
        assert len(results) == 1
        r = results[0]
        assert r["quantity_sold"] == 3
        assert r["total_revenue"] == 300.0
        assert r["total_cost"] == 180.0
        assert r["profit"] == 120.0

    def test_nc_full_reversal_zero_profit(self, client, seed_all):
        """Sale 5×100, NC 5×100 → revenue=0, cost=0, profit=0."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=5, unit_price=100.0)

        results = _get_profit_report(client, s)
        if len(results) > 0:
            r = results[0]
            assert r["quantity_sold"] == 0
            assert r["total_revenue"] == 0.0
            assert r["total_cost"] == 0.0
            assert r["profit"] == 0.0

    def test_excludes_nota_venta(self, client, seed_all):
        """NOTA_VENTA does not appear in profit report."""
        s = seed_all
        _create_sale(client, s, doc_type="NOTA_VENTA", series="NV01",
                     client_key="dni_client", qty=5, unit_price=100.0)

        results = _get_profit_report(client, s)
        assert len(results) == 0

    def test_excludes_anulado(self, client, seed_all):
        """Anulado sale does not appear in profit report."""
        s = seed_all
        sale = _create_sale(client, s, qty=5, unit_price=100.0)
        _anular(client, s, sale["id"])

        results = _get_profit_report(client, s)
        assert len(results) == 0

    def test_mixed_scenario(self, client, seed_all):
        """Real sale + NC + NV + anulado → only net of real sale counts.

        Sale A: 5×100 = 500 (facturado)
        NC:     2×100 = 200 (against A)
        Sale B: 3×100 = 300 (anulado → excluded)
        Sale C: 4×100 = 400 (nota_venta → excluded)

        Expected: qty=3, revenue=300, cost=180, profit=120
        """
        s = seed_all
        sale_a = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale_a["id"], qty=2, unit_price=100.0)

        sale_b = _create_sale(client, s, qty=3, unit_price=100.0)
        _anular(client, s, sale_b["id"])

        _create_sale(client, s, doc_type="NOTA_VENTA", series="NV01",
                     client_key="dni_client", qty=4, unit_price=100.0)

        results = _get_profit_report(client, s)
        assert len(results) == 1
        r = results[0]
        assert r["quantity_sold"] == 3
        assert r["total_revenue"] == 300.0
        assert r["total_cost"] == 180.0
        assert r["profit"] == 120.0


# ===================================================================
# MIXED / INTEGRATION
# ===================================================================

class TestReportIntegration:
    """Cross-endpoint consistency: all reports agree on the same scenario."""

    def test_all_reports_consistent(self, client, seed_all):
        """Sale 5×100 + NC 2×100 → all reports show net 3×100=300."""
        s = seed_all
        sale = _create_and_facturar(client, s, qty=5, unit_price=100.0)
        _create_nc(client, s, sale["id"], qty=2, unit_price=100.0)

        # Dashboard
        dash = _get_dashboard(client, s)
        assert dash["today_sales"] == 1
        assert dash["today_total"] == 300.0

        # Top products
        top = _get_top_products(client, s)
        assert top[0]["quantity_sold"] == 3
        assert top[0]["total_revenue"] == 300.0

        # Profit report
        profit = _get_profit_report(client, s)
        assert profit[0]["quantity_sold"] == 3
        assert profit[0]["total_revenue"] == 300.0
        assert profit[0]["profit"] == 120.0  # 300 - (3 × 60)
