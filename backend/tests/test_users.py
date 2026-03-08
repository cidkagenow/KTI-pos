"""User management CRUD tests (admin-only)."""


def test_list_users(client, admin_user, admin_headers):
    r = client.get("/api/v1/users", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_create_user(client, admin_user, admin_headers):
    r = client.post("/api/v1/users", headers=admin_headers, json={
        "username": "nuevo",
        "password": "Secure123",
        "full_name": "Nuevo User",
        "role": "VENTAS",
    })
    assert r.status_code == 201
    assert r.json()["username"] == "nuevo"
    assert r.json()["role"] == "VENTAS"


def test_create_user_duplicate(client, admin_user, admin_headers):
    r = client.post("/api/v1/users", headers=admin_headers, json={
        "username": "admin_test",
        "password": "pass",
        "full_name": "Dup",
        "role": "VENTAS",
    })
    assert r.status_code == 400


def test_update_user(client, admin_user, ventas_user, admin_headers):
    r = client.put(f"/api/v1/users/{ventas_user.id}", headers=admin_headers, json={
        "full_name": "Updated Name",
    })
    assert r.status_code == 200
    assert r.json()["full_name"] == "Updated Name"


def test_change_password(client, admin_user, ventas_user, admin_headers):
    r = client.put(f"/api/v1/users/{ventas_user.id}/password", headers=admin_headers, json={
        "new_password": "NewSecure456",
    })
    assert r.status_code == 200

    # Verify new password works
    r2 = client.post("/api/v1/auth/login", json={
        "username": "ventas_test",
        "password": "NewSecure456",
    })
    assert r2.status_code == 200


def test_deactivate_user(client, admin_user, ventas_user, admin_headers):
    r = client.delete(f"/api/v1/users/{ventas_user.id}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_deactivated_user_cannot_login(client, admin_user, ventas_user, admin_headers):
    client.delete(f"/api/v1/users/{ventas_user.id}", headers=admin_headers)
    r = client.post("/api/v1/auth/login", json={
        "username": "ventas_test",
        "password": "ventas123",
    })
    assert r.status_code == 401
