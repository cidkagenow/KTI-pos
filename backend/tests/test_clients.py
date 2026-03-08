"""Client CRUD + search tests."""


def test_create_client(client, admin_user, admin_headers):
    r = client.post("/api/v1/clients", headers=admin_headers, json={
        "doc_type": "RUC",
        "doc_number": "20999888777",
        "business_name": "Empresa Nueva",
    })
    assert r.status_code == 201
    assert r.json()["business_name"] == "Empresa Nueva"
    assert r.json()["doc_type"] == "RUC"


def test_list_clients(client, admin_user, admin_headers, seed_ruc_client):
    r = client.get("/api/v1/clients", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_search_clients(client, admin_user, admin_headers, seed_ruc_client):
    r = client.get("/api/v1/clients/search?q=Empresa", headers=admin_headers)
    assert r.status_code == 200
    assert any("Empresa" in c["business_name"] for c in r.json())


def test_update_client_admin_only(client, ventas_user, ventas_headers, seed_ruc_client):
    r = client.put(
        f"/api/v1/clients/{seed_ruc_client.id}",
        headers=ventas_headers,
        json={"business_name": "Changed"},
    )
    assert r.status_code == 403
