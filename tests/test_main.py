from fastapi import Response
from fastapi.testclient import TestClient

from gateway import health_checks, main
from gateway.main import app

client = TestClient(app)


def test_ping_returns_ok_without_any_backend_call():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_200_when_all_checks_pass(monkeypatch):
    async def _fake_check_all():
        return {
            "status": "healthy",
            "checks": {
                "redis": {"status": "healthy", "message": "Redis reachable."},
                "backend_service": {"status": "healthy", "message": "Backend reachable."},
            },
        }

    monkeypatch.setattr(health_checks, "check_all", _fake_check_all)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_health_returns_503_when_a_check_fails(monkeypatch):
    async def _fake_check_all():
        return {
            "status": "unhealthy",
            "checks": {
                "redis": {"status": "unhealthy", "message": "redis down"},
                "backend_service": {"status": "healthy", "message": "Backend reachable."},
            },
        }

    monkeypatch.setattr(health_checks, "check_all", _fake_check_all)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"


def test_cors_allows_the_real_frontend_origin():
    response = client.get("/ping", headers={"Origin": "https://hrb-chatbot-ui.rvsree.dev"})
    assert response.headers["access-control-allow-origin"] == "https://hrb-chatbot-ui.rvsree.dev"


def test_cors_allows_any_localhost_port():
    response = client.get("/ping", headers={"Origin": "http://localhost:5174"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"


def test_cors_rejects_an_unrelated_origin():
    response = client.get("/ping", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


def test_invalid_body_on_a_known_path_is_422_and_never_forwarded(monkeypatch):
    async def _forward_request_should_not_be_called(request, backend_base_url, client=None):
        raise AssertionError("forward_request() must not be called when contract validation fails")

    monkeypatch.setattr(main, "forward_request", _forward_request_should_not_be_called)

    response = client.post("/v1/genai-rag-retrieval/query", json={})  # missing required "query"

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_valid_body_on_a_known_path_still_gets_forwarded(monkeypatch):
    async def _fake_forward_request(request, backend_base_url, client=None):
        return Response(content=b'{"answer": "ok"}', status_code=200, media_type="application/json")

    monkeypatch.setattr(main, "forward_request", _fake_forward_request)

    response = client.post("/v1/genai-rag-retrieval/query", json={"query": "What's the dental plan?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "ok"}


def test_unscoped_path_skips_validation_entirely(monkeypatch):
    async def _fake_forward_request(request, backend_base_url, client=None):
        return Response(content=b'{"ok": true}', status_code=200, media_type="application/json")

    monkeypatch.setattr(main, "forward_request", _fake_forward_request)

    response = client.post("/v1/some-unscoped-endpoint", json={"anything": "goes"})

    assert response.status_code == 200
