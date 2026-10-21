from fastapi.testclient import TestClient

from gateway.main import app

client = TestClient(app)


def test_ping_returns_ok_without_any_backend_call():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_the_real_frontend_origin():
    response = client.get("/ping", headers={"Origin": "https://hrb-chatbot-ui.rvsree.dev"})
    assert response.headers["access-control-allow-origin"] == "https://hrb-chatbot-ui.rvsree.dev"


def test_cors_allows_any_localhost_port():
    response = client.get("/ping", headers={"Origin": "http://localhost:5174"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"


def test_cors_rejects_an_unrelated_origin():
    response = client.get("/ping", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers
