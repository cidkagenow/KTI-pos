#!/usr/bin/env python3
"""
KTI-POS System Analysis Script
Tests all critical flows including SUNAT beta integration.
Run inside Docker: docker compose exec backend python scripts/system_analysis.py
"""

import json
import os
import sys
import time
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE_URL = "http://localhost:8000/api/v1"
RESULTS = []
CREATED_SALE_IDS = []


def log(section, test, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append({"section": section, "test": test, "status": status, "detail": detail})
    icon = "\033[92m✓\033[0m" if ok else "\033[91m✗\033[0m"
    print(f"  {icon} {test}" + (f" — {detail}" if detail else ""))


def get_token(username, password):
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"]
    return None


def headers(token):
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════
# 1. AUTHENTICATION
# ═══════════════════════════════════════════════════════════════
def test_auth():
    print("\n\033[1m═══ 1. AUTENTICACIÓN ═══\033[0m")

    admin_token = get_token("admin", "admin123")
    log("Auth", "Login ADMIN", admin_token is not None)

    # Test invalid login
    bad_token = get_token("admin", "wrongpassword")
    log("Auth", "Login con contraseña incorrecta rechazado", bad_token is None)

    # Test protected route without token
    r = requests.get(f"{BASE_URL}/sales")
    log("Auth", "Ruta protegida sin token = 401", r.status_code == 401)

    return admin_token


# ═══════════════════════════════════════════════════════════════
# 2. CATALOGS
# ═══════════════════════════════════════════════════════════════
def test_catalogs(token):
    print("\n\033[1m═══ 2. CATÁLOGOS ═══\033[0m")
    h = headers(token)

    r = requests.get(f"{BASE_URL}/catalogs/brands", headers=h)
    brands = r.json() if r.status_code == 200 else []
    log("Catalogs", "Listar marcas", r.status_code == 200, f"{len(brands)} marcas")

    r = requests.get(f"{BASE_URL}/catalogs/categories", headers=h)
    cats = r.json() if r.status_code == 200 else []
    log("Catalogs", "Listar categorías", r.status_code == 200, f"{len(cats)} categorías")

    r = requests.get(f"{BASE_URL}/catalogs/warehouses", headers=h)
    wh = r.json() if r.status_code == 200 else []
    log("Catalogs", "Listar almacenes", r.status_code == 200, f"{len(wh)} almacenes")

    r = requests.get(f"{BASE_URL}/catalogs/document-series", headers=h)
    log("Catalogs", "Series de documentos", r.status_code == 200)

    return wh[0]["id"] if wh else None


# ═══════════════════════════════════════════════════════════════
# 3. PRODUCTS
# ═══════════════════════════════════════════════════════════════
def test_products(token):
    print("\n\033[1m═══ 3. PRODUCTOS ═══\033[0m")
    h = headers(token)

    r = requests.get(f"{BASE_URL}/products", headers=h)
    products = r.json() if r.status_code == 200 else []
    log("Products", "Listar productos", r.status_code == 200, f"{len(products)} productos")

    active = [p for p in products if p.get("is_active")]
    log("Products", "Productos activos", len(active) > 0, f"{len(active)} activos")

    with_stock = [p for p in products if (p.get("total_stock") or 0) > 0]
    log("Products", "Productos con stock > 0", len(with_stock) > 0, f"{len(with_stock)} con stock")

    with_price = [p for p in products if (p.get("unit_price") or 0) > 0]
    log("Products", "Productos con precio > 0", True,
        f"{len(with_price)} con precio" + (" (⚠ muchos sin precio)" if len(with_price) < len(active) * 0.5 else ""))

    return products


# ═══════════════════════════════════════════════════════════════
# 4. CLIENTS
# ═══════════════════════════════════════════════════════════════
def test_clients(token):
    print("\n\033[1m═══ 4. CLIENTES ═══\033[0m")
    h = headers(token)

    r = requests.get(f"{BASE_URL}/clients", headers=h)
    clients = r.json() if r.status_code == 200 else []
    log("Clients", "Listar clientes", r.status_code == 200, f"{len(clients)} clientes")

    ruc_clients = [c for c in clients if c.get("doc_type") == "RUC" and c.get("doc_number")]
    log("Clients", "Clientes con RUC", len(ruc_clients) > 0, f"{len(ruc_clients)} con RUC")

    dni_clients = [c for c in clients if c.get("doc_type") == "DNI" and c.get("doc_number")]
    log("Clients", "Clientes con DNI", len(dni_clients) > 0, f"{len(dni_clients)} con DNI")

    # Search test
    r = requests.get(f"{BASE_URL}/clients?search=varios", headers=h)
    log("Clients", "Búsqueda de 'varios'", r.status_code == 200)

    return clients, ruc_clients, dni_clients


# ═══════════════════════════════════════════════════════════════
# 5. INVENTORY
# ═══════════════════════════════════════════════════════════════
def test_inventory(token):
    print("\n\033[1m═══ 5. INVENTARIO ═══\033[0m")
    h = headers(token)

    r = requests.get(f"{BASE_URL}/inventory", headers=h)
    inv = r.json() if r.status_code == 200 else []
    log("Inventory", "Listar inventario", r.status_code == 200, f"{len(inv)} registros")

    r = requests.get(f"{BASE_URL}/inventory/movements", headers=h)
    log("Inventory", "Listar movimientos", r.status_code == 200)

    r = requests.get(f"{BASE_URL}/inventory/alerts", headers=h)
    alerts = r.json() if r.status_code == 200 else []
    log("Inventory", "Alertas de stock bajo", r.status_code == 200, f"{len(alerts)} alertas")


# ═══════════════════════════════════════════════════════════════
# 6. SALES CRUD
# ═══════════════════════════════════════════════════════════════
def test_sales(token, products, ruc_clients, dni_clients, warehouse_id):
    print("\n\033[1m═══ 6. VENTAS ═══\033[0m")
    h = headers(token)

    # Find a product with stock
    prod = None
    for p in products:
        if (p.get("total_stock") or 0) > 0:
            prod = p
            break

    if not prod:
        log("Sales", "Encontrar producto con stock", False, "No hay productos con stock > 0")
        return None, None, None

    price = prod.get("unit_price") or 10.0  # Default test price if 0
    log("Sales", "Producto de prueba", True,
        f"{prod['code']} - {prod['name']} (stock: {prod['total_stock']}, precio: {price})")

    # --- NOTA DE VENTA ---
    nv_payload = {
        "doc_type": "NOTA_VENTA",
        "series": "NV01",
        "client_id": (dni_clients[0]["id"] if dni_clients else ruc_clients[0]["id"] if ruc_clients else None),
        "warehouse_id": warehouse_id,
        "items": [{"product_id": prod["id"], "quantity": 1, "unit_price": price, "discount_pct": 0}],
    }
    r = requests.post(f"{BASE_URL}/sales", headers=h, json=nv_payload)
    nv_ok = r.status_code == 201
    nv_id = r.json().get("id") if nv_ok else None
    log("Sales", "Crear NOTA_VENTA", nv_ok, f"ID: {nv_id}" if nv_ok else r.text[:200])
    if nv_id:
        CREATED_SALE_IDS.append(nv_id)

    # Delete NV (should work - PREVENTA)
    if nv_id:
        r = requests.delete(f"{BASE_URL}/sales/{nv_id}", headers=h)
        log("Sales", "Eliminar PREVENTA", r.status_code == 200)

    # --- BOLETA ---
    # Find CLIENTES VARIOS or a DNI client
    boleta_client_id = None
    for c in (dni_clients or []):
        boleta_client_id = c["id"]
        break
    if not boleta_client_id:
        # Try any client
        r2 = requests.get(f"{BASE_URL}/clients?search=varios", headers=h)
        varios = r2.json() if r2.status_code == 200 else []
        if varios:
            boleta_client_id = varios[0]["id"]

    boleta_payload = {
        "doc_type": "BOLETA",
        "series": "B001",
        "client_id": boleta_client_id,
        "warehouse_id": warehouse_id,
        "items": [{"product_id": prod["id"], "quantity": 1, "unit_price": price, "discount_pct": 0}],
    }
    r = requests.post(f"{BASE_URL}/sales", headers=h, json=boleta_payload)
    boleta_ok = r.status_code == 201
    boleta_id = r.json().get("id") if boleta_ok else None
    log("Sales", "Crear BOLETA", boleta_ok, f"ID: {boleta_id}" if boleta_ok else r.text[:200])
    if boleta_id:
        CREATED_SALE_IDS.append(boleta_id)

    # --- FACTURA ---
    factura_client_id = ruc_clients[0]["id"] if ruc_clients else None
    if not factura_client_id:
        log("Sales", "Crear FACTURA", False, "No hay clientes con RUC")
        return boleta_id, None, prod

    factura_payload = {
        "doc_type": "FACTURA",
        "series": "F001",
        "client_id": factura_client_id,
        "warehouse_id": warehouse_id,
        "items": [{"product_id": prod["id"], "quantity": 1, "unit_price": price, "discount_pct": 0}],
    }
    r = requests.post(f"{BASE_URL}/sales", headers=h, json=factura_payload)
    factura_ok = r.status_code == 201
    factura_id = r.json().get("id") if factura_ok else None
    log("Sales", "Crear FACTURA", factura_ok, f"ID: {factura_id}" if factura_ok else r.text[:200])
    if factura_id:
        CREATED_SALE_IDS.append(factura_id)

    # List sales
    r = requests.get(f"{BASE_URL}/sales", headers=h)
    log("Sales", "Listar ventas", r.status_code == 200)

    return boleta_id, factura_id, prod


# ═══════════════════════════════════════════════════════════════
# 7. FACTURAR (emit to SUNAT)
# ═══════════════════════════════════════════════════════════════
def test_facturar(token, boleta_id, factura_id):
    print("\n\033[1m═══ 7. FACTURAR ═══\033[0m")
    h = headers(token)

    boleta_facturado = False
    factura_facturado = False

    if boleta_id:
        r = requests.post(f"{BASE_URL}/sales/{boleta_id}/facturar", headers=h)
        boleta_facturado = r.status_code == 200
        detail = ""
        if boleta_facturado:
            body = r.json()
            detail = f"status={body.get('status')}, sunat={body.get('sunat_status', 'N/A')}"
        else:
            detail = r.text[:200]
        log("Facturar", "Facturar BOLETA", boleta_facturado, detail)

    if factura_id:
        r = requests.post(f"{BASE_URL}/sales/{factura_id}/facturar", headers=h)
        factura_facturado = r.status_code == 200
        detail = ""
        if factura_facturado:
            body = r.json()
            detail = f"status={body.get('status')}, sunat={body.get('sunat_status', 'N/A')}"
        else:
            detail = r.text[:200]
        log("Facturar", "Facturar FACTURA", factura_facturado, detail)

    return boleta_facturado, factura_facturado


# ═══════════════════════════════════════════════════════════════
# 8. SUNAT - ENVIAR FACTURA
# ═══════════════════════════════════════════════════════════════
def test_sunat_factura(token, factura_id):
    print("\n\033[1m═══ 8. SUNAT — ENVIAR FACTURA ═══\033[0m")
    h = headers(token)

    if not factura_id:
        log("SUNAT-Factura", "Enviar factura a SUNAT", False, "No se creó factura")
        return

    r = requests.post(f"{BASE_URL}/sunat/facturas/{factura_id}/enviar", headers=h)
    ok = r.status_code == 200
    if ok:
        body = r.json()
        sunat_status = body.get("sunat_status", "?")
        desc = body.get("sunat_description", "")[:100]
        log("SUNAT-Factura", "Enviar factura a SUNAT beta", True, f"{sunat_status}: {desc}")

        # Check if ACEPTADO
        log("SUNAT-Factura", "Factura ACEPTADA por SUNAT beta",
            sunat_status == "ACEPTADO", sunat_status)
    else:
        log("SUNAT-Factura", "Enviar factura a SUNAT beta", False, r.text[:300])


# ═══════════════════════════════════════════════════════════════
# 9. SUNAT - RESUMEN BOLETAS
# ═══════════════════════════════════════════════════════════════
def test_sunat_resumen(token):
    print("\n\033[1m═══ 9. SUNAT — RESUMEN BOLETAS ═══\033[0m")
    h = headers(token)

    today = date.today().isoformat()

    # Check pending
    r = requests.get(f"{BASE_URL}/sunat/resumen-boletas/pendientes?fecha={today}", headers=h)
    if r.status_code == 200:
        body = r.json()
        nuevas = body.get("nuevas", 0)
        anuladas = body.get("anuladas", 0)
        log("SUNAT-Resumen", "Boletas pendientes", True, f"nuevas={nuevas}, anuladas={anuladas}")
    else:
        log("SUNAT-Resumen", "Boletas pendientes", False, r.text[:200])
        return

    if nuevas == 0 and anuladas == 0:
        log("SUNAT-Resumen", "Enviar resumen", True, "No hay boletas pendientes (OK)")
        return

    # Send resumen
    r = requests.post(f"{BASE_URL}/sunat/resumen-boletas", headers=h, json={"fecha": today})
    if r.status_code == 200:
        body = r.json()
        status = body.get("sunat_status", "?")
        ticket = body.get("ticket", "")
        log("SUNAT-Resumen", "Enviar resumen diario", True, f"{status}, ticket={ticket}")

        # If we got a ticket, check status
        if ticket:
            time.sleep(3)  # Wait a bit for SUNAT to process
            r2 = requests.post(f"{BASE_URL}/sunat/ticket/{ticket}/status", headers=h)
            if r2.status_code == 200:
                body2 = r2.json()
                st = body2.get("sunat_status", "?")
                desc = body2.get("sunat_description", "")[:100]
                log("SUNAT-Resumen", "Consultar ticket resumen", True, f"{st}: {desc}")
            else:
                log("SUNAT-Resumen", "Consultar ticket resumen", False, r2.text[:200])
    else:
        log("SUNAT-Resumen", "Enviar resumen diario", False, r.text[:300])


# ═══════════════════════════════════════════════════════════════
# 10. SUNAT - ANULACIÓN Y BAJA
# ═══════════════════════════════════════════════════════════════
def test_sunat_baja(token, factura_id):
    print("\n\033[1m═══ 10. SUNAT — ANULACIÓN Y BAJA ═══\033[0m")
    h = headers(token)

    if not factura_id:
        log("SUNAT-Baja", "Anular factura", False, "No se creó factura")
        return

    # Anular the factura
    r = requests.post(f"{BASE_URL}/sales/{factura_id}/anular", headers=h,
                      json={"reason": "Test de análisis de sistema"})
    log("SUNAT-Baja", "Anular factura", r.status_code == 200,
        r.json().get("status", "") if r.status_code == 200 else r.text[:200])

    # Send baja
    r = requests.post(f"{BASE_URL}/sunat/baja", headers=h, json={
        "sale_id": factura_id,
        "motivo": "ANULACION POR PRUEBA DE SISTEMA",
    })
    if r.status_code == 200:
        body = r.json()
        status = body.get("sunat_status", "?")
        ticket = body.get("ticket", "")
        log("SUNAT-Baja", "Enviar baja a SUNAT beta", True, f"{status}, ticket={ticket}")

        if ticket:
            time.sleep(3)
            r2 = requests.post(f"{BASE_URL}/sunat/ticket/{ticket}/status", headers=h)
            if r2.status_code == 200:
                body2 = r2.json()
                st = body2.get("sunat_status", "?")
                log("SUNAT-Baja", "Consultar ticket baja", True, st)
            else:
                log("SUNAT-Baja", "Consultar ticket baja", False, r2.text[:200])
    else:
        log("SUNAT-Baja", "Enviar baja a SUNAT beta", False, r.text[:300])


# ═══════════════════════════════════════════════════════════════
# 11. REPORTS
# ═══════════════════════════════════════════════════════════════
def test_reports(token):
    print("\n\033[1m═══ 11. REPORTES ═══\033[0m")
    h = headers(token)

    today = date.today().isoformat()
    first_day = date.today().replace(day=1).isoformat()

    r = requests.get(f"{BASE_URL}/reports/sales-by-period?from_date={first_day}&to_date={today}&group_by=day", headers=h)
    log("Reports", "Ventas por periodo (día)", r.status_code == 200)

    r = requests.get(f"{BASE_URL}/reports/sales-by-period?from_date={first_day}&to_date={today}&group_by=week", headers=h)
    if r.status_code == 200:
        data = r.json()
        has_w = all("W" in d.get("period", "") for d in data) if data else True
        log("Reports", "Ventas por periodo (semana) — formato W", has_w, str(data[:2]) if data else "sin datos")
    else:
        log("Reports", "Ventas por periodo (semana)", False)

    r = requests.get(f"{BASE_URL}/reports/top-products?from_date={first_day}&to_date={today}", headers=h)
    log("Reports", "Top productos", r.status_code == 200)

    r = requests.get(f"{BASE_URL}/reports/dashboard", headers=h)
    if r.status_code == 200:
        body = r.json()
        log("Reports", "Dashboard", True,
            f"ventas_hoy={body.get('today_sales')}, total_hoy={body.get('today_total')}, stock_bajo={body.get('low_stock_count')}")
    else:
        log("Reports", "Dashboard", False)


# ═══════════════════════════════════════════════════════════════
# 12. TRABAJADORES
# ═══════════════════════════════════════════════════════════════
def test_trabajadores(token):
    print("\n\033[1m═══ 12. TRABAJADORES ═══\033[0m")
    h = headers(token)

    r = requests.get(f"{BASE_URL}/trabajadores", headers=h)
    log("Trabajadores", "Listar trabajadores", r.status_code == 200,
        f"{len(r.json())} trabajadores" if r.status_code == 200 else "")

    r = requests.get(f"{BASE_URL}/trabajadores/active", headers=h)
    log("Trabajadores", "Listar activos", r.status_code == 200)

    today = date.today().isoformat()
    r = requests.get(f"{BASE_URL}/trabajadores/asistencia?fecha={today}", headers=h)
    log("Trabajadores", "Asistencia hoy", r.status_code == 200,
        f"{len(r.json())} registros" if r.status_code == 200 else "")


# ═══════════════════════════════════════════════════════════════
# 13. SUNAT CONFIG CHECK
# ═══════════════════════════════════════════════════════════════
def test_sunat_config():
    print("\n\033[1m═══ 13. CONFIGURACIÓN SUNAT ═══\033[0m")

    from app.config import settings

    log("Config", "SUNAT_ENV", True, settings.SUNAT_ENV)
    log("Config", "EMPRESA_RUC", bool(settings.EMPRESA_RUC), settings.EMPRESA_RUC)
    log("Config", "EMPRESA_RAZON_SOCIAL", bool(settings.EMPRESA_RAZON_SOCIAL), settings.EMPRESA_RAZON_SOCIAL)
    log("Config", "SOL_USER configurado", bool(settings.SUNAT_SOL_USER), settings.SUNAT_SOL_USER)

    import os
    cert_exists = os.path.exists(settings.SUNAT_CERT_PATH) if settings.SUNAT_CERT_PATH else False
    log("Config", "Certificado digital existe",
        cert_exists or settings.SUNAT_ENV == "beta",
        settings.SUNAT_CERT_PATH or "(no configurado — OK para beta)")

    if cert_exists:
        try:
            from app.services.sunat_signer import _load_cert
            _load_cert()
            log("Config", "Certificado digital se carga correctamente", True)
        except Exception as e:
            log("Config", "Certificado digital se carga correctamente", False, str(e))

    log("Config", "GEMINI_API_KEY configurada", bool(settings.GEMINI_API_KEY),
        "Sí" if settings.GEMINI_API_KEY else "No (chatbot no funcionará)")


# ═══════════════════════════════════════════════════════════════
# 14. CHATBOT
# ═══════════════════════════════════════════════════════════════
def test_chatbot(token):
    print("\n\033[1m═══ 14. CHATBOT ═══\033[0m")
    h = headers(token)

    r = requests.post(f"{BASE_URL}/chat", headers=h, json={
        "message": "hola",
        "session_id": "test-analysis",
    })
    if r.status_code == 200:
        reply = r.json().get("reply", "")
        log("Chatbot", "Respuesta a 'hola'", bool(reply), reply[:100])
    else:
        log("Chatbot", "Respuesta a 'hola'", False, r.text[:200])


# ═══════════════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════════════
def cleanup(token):
    """Delete test sales that are still in PREVENTA."""
    h = headers(token)
    for sid in CREATED_SALE_IDS:
        try:
            requests.delete(f"{BASE_URL}/sales/{sid}", headers=h)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print("\033[1m" + "=" * 60)
    print("  KTI-POS — ANÁLISIS DE SISTEMA")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\033[0m")

    # 1. Auth
    admin_token = test_auth()
    if not admin_token:
        print("\n\033[91mERROR CRÍTICO: No se pudo autenticar como admin. Abortando.\033[0m")
        sys.exit(1)

    # 2-5. Basic modules
    warehouse_id = test_catalogs(admin_token)
    products = test_products(admin_token)
    clients, ruc_clients, dni_clients = test_clients(admin_token)
    test_inventory(admin_token)

    # 6. Sales
    boleta_id, factura_id, prod = test_sales(admin_token, products, ruc_clients, dni_clients, warehouse_id)

    # 7. Facturar
    boleta_ok, factura_ok = test_facturar(admin_token, boleta_id, factura_id)

    # 8-10. SUNAT
    if factura_ok:
        test_sunat_factura(admin_token, factura_id)
    else:
        print("\n\033[1m═══ 8. SUNAT — ENVIAR FACTURA ═══\033[0m")
        log("SUNAT-Factura", "Enviar factura", False, "Factura no se facturó")

    test_sunat_resumen(admin_token)

    if factura_ok:
        test_sunat_baja(admin_token, factura_id)
    else:
        print("\n\033[1m═══ 10. SUNAT — BAJA ═══\033[0m")
        log("SUNAT-Baja", "Baja", False, "No hay factura para anular")

    # 11-14. Other modules
    test_reports(admin_token)
    test_trabajadores(admin_token)
    test_sunat_config()
    test_chatbot(admin_token)

    # Summary
    print("\n\033[1m" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60 + "\033[0m")

    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    total = len(RESULTS)

    print(f"\n  Total: {total} tests")
    print(f"  \033[92mPASS: {passed}\033[0m")
    if failed > 0:
        print(f"  \033[91mFAIL: {failed}\033[0m")
        print("\n  Tests fallidos:")
        for r in RESULTS:
            if r["status"] == "FAIL":
                print(f"    \033[91m✗ [{r['section']}] {r['test']}: {r['detail']}\033[0m")
    else:
        print(f"\n  \033[92m¡Todos los tests pasaron! El sistema está listo.\033[0m")

    # Note about SUNAT
    from app.config import settings
    if settings.SUNAT_ENV == "beta":
        print(f"\n  \033[93m⚠ SUNAT en modo BETA. Para producción, configurar:\033[0m")
        print(f"    SUNAT_ENV=production")
        print(f"    SUNAT_SOL_USER=tu_usuario_sol")
        print(f"    SUNAT_SOL_PASSWORD=tu_password_sol")
        print(f"    SUNAT_CERT_PATH=/app/certs/certificado.pfx")
        print(f"    SUNAT_CERT_PASSWORD=tu_password_cert")

    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
