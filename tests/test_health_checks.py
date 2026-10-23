import fakeredis
import httpx
import pytest

from gateway.health_checks import check_all, check_backend_service, check_redis


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


def test_check_redis_healthy_when_reachable(monkeypatch, fake_redis):
    monkeypatch.setattr("gateway.health_checks.get_redis_client", lambda: fake_redis)
    result = check_redis()
    assert result == {"status": "healthy", "message": "Redis reachable."}


def test_check_redis_unhealthy_when_unreachable(monkeypatch):
    class BrokenRedis:
        def ping(self):
            raise ConnectionError("redis down")

    monkeypatch.setattr("gateway.health_checks.get_redis_client", lambda: BrokenRedis())
    result = check_redis()
    assert result["status"] == "unhealthy"
    assert "redis down" in result["message"]


async def test_check_backend_service_healthy_on_200_carries_backend_report():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "healthy", "embedding_model": "text-embedding-3-small"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    result = await check_backend_service("http://backend", client=client)
    assert result["status"] == "healthy"
    assert result["backend_report"]["embedding_model"] == "text-embedding-3-small"


async def test_check_backend_service_unhealthy_on_non_200_has_null_report():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    result = await check_backend_service("http://backend", client=client)
    assert result["status"] == "unhealthy"
    assert "503" in result["message"]
    assert result["backend_report"] is None


async def test_check_backend_service_unhealthy_on_connection_error_has_null_report():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    result = await check_backend_service("http://backend", client=client)
    assert result["status"] == "unhealthy"
    assert "connection refused" in result["message"]
    assert result["backend_report"] is None


async def test_check_backend_service_unhealthy_on_non_json_body_has_null_report():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    result = await check_backend_service("http://backend", client=client)
    assert result["status"] == "unhealthy"
    assert result["backend_report"] is None


async def test_check_all_overall_healthy_when_both_checks_pass(monkeypatch, fake_redis):
    monkeypatch.setattr("gateway.health_checks.get_redis_client", lambda: fake_redis)

    async def _fake_check_backend_service(backend_base_url):
        return {"status": "healthy", "message": "Backend reachable."}

    monkeypatch.setattr("gateway.health_checks.check_backend_service", _fake_check_backend_service)

    report = await check_all()
    assert report["status"] == "healthy"
    assert report["checks"]["redis"]["status"] == "healthy"
    assert report["checks"]["backend_service"]["status"] == "healthy"


async def test_check_all_overall_unhealthy_when_one_check_fails(monkeypatch):
    class BrokenRedis:
        def ping(self):
            raise ConnectionError("redis down")

    monkeypatch.setattr("gateway.health_checks.get_redis_client", lambda: BrokenRedis())

    async def _fake_check_backend_service(backend_base_url):
        return {"status": "healthy", "message": "Backend reachable."}

    monkeypatch.setattr("gateway.health_checks.check_backend_service", _fake_check_backend_service)

    report = await check_all()
    assert report["status"] == "unhealthy"
