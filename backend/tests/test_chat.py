"""Chat (Gemini AI) tests with mocked service."""

from unittest.mock import patch


def test_send_message(client, admin_user, admin_headers):
    with patch("app.api.chat.chat_with_gemini") as mock_gemini:
        mock_gemini.return_value = "Hola, ¿en qué puedo ayudarte?"
        r = client.post("/api/v1/chat", headers=admin_headers, json={
            "message": "Hola",
        })

    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "Hola, ¿en qué puedo ayudarte?"
    assert len(body["messages"]) >= 2  # user + model


def test_chat_history(client, admin_user, admin_headers):
    with patch("app.api.chat.chat_with_gemini") as mock_gemini:
        mock_gemini.return_value = "Respuesta test"
        client.post("/api/v1/chat", headers=admin_headers, json={"message": "Msg 1"})
        client.post("/api/v1/chat", headers=admin_headers, json={"message": "Msg 2"})

    r = client.get("/api/v1/chat/history", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 4  # 2 user + 2 model messages


def test_clear_history(client, admin_user, admin_headers):
    with patch("app.api.chat.chat_with_gemini") as mock_gemini:
        mock_gemini.return_value = "OK"
        client.post("/api/v1/chat", headers=admin_headers, json={"message": "Test"})

    r = client.delete("/api/v1/chat/history", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r2 = client.get("/api/v1/chat/history", headers=admin_headers)
    assert len(r2.json()) == 0
