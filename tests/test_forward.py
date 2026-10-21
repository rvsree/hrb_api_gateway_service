import httpx
import pytest
from starlette.requests import Request

from gateway.routing.forward import BackendUnavailableError, _breaker, forward_request


def _make_request(method="GET", path="/v1/genai-rag-retrieval/query", body=b"", headers=None) -> Request:
    headers = headers or {}
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


@pytest.fixture(autouse=True)
def reset_breaker():
    _breaker._consecutive_failures = 0
    _breaker._last_failure_at = None
    yield
    _breaker._consecutive_failures = 0
    _breaker._last_failure_at = None


async def test_forward_request_proxies_to_backend_unchanged():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/genai-rag-retrieval/query"
        assert "x-request-id" in {k.lower() for k in request.headers.keys()}
        return httpx.Response(200, json={"answer": "42"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    request = _make_request(body=b'{"question": "test"}')

    response = await forward_request(request, "http://backend", client=client)

    assert response.status_code == 200
    assert b"42" in response.body


async def test_forward_request_raises_backend_unavailable_on_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    request = _make_request()

    with pytest.raises(BackendUnavailableError):
        await forward_request(request, "http://backend", client=client)


async def test_forward_request_trips_circuit_breaker_after_repeated_failures():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")

    for _ in range(2):
        with pytest.raises(BackendUnavailableError):
            await forward_request(_make_request(), "http://backend", client=client)

    # third call should fail fast via the breaker, not attempt a real call
    with pytest.raises(BackendUnavailableError):
        await forward_request(_make_request(), "http://backend", client=client)
