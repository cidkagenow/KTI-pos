"""Authentication & authorization tests."""


def test_login_success(client, admin_user):
    r = client.post("/api/v1/auth/login", json={
        "username": "admin_test",
        "password": "admin123",
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["user"]["username"] == "admin_test"
    assert body["user"]["role"] == "ADMIN"


def test_login_wrong_password(client, admin_user):
    r = client.post("/api/v1/auth/login", json={
        "username": "admin_test",
        "password": "wrong",
    })
    assert r.status_code == 401


def test_login_nonexistent_user(client, db_session):
    r = client.post("/api/v1/auth/login", json={
        "username": "ghost",
        "password": "nope",
    })
    assert r.status_code == 401


def test_me_authenticated(client, admin_user, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "admin_test"


def test_me_no_token(client, db_session):
    r = client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)  # depends on FastAPI version


def test_me_invalid_token(client, db_session):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


def test_admin_route_blocked_for_ventas(client, ventas_user, ventas_headers):
    """VENTAS role cannot access admin-only endpoints (e.g. create user)."""
    r = client.post("/api/v1/users", headers=ventas_headers, json={
        "username": "new", "password": "pass", "full_name": "New", "role": "VENTAS",
    })
    assert r.status_code == 403
