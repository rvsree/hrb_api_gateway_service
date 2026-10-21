"""Generic reverse-proxy forwarding - new code (see ROADMAP.md's Phase 3 scope note:
rag_ingestion_service/rag_retrieval_service don't exist yet, so this proves the
forwarding mechanism against one configurable backend first, matching the original
cutover plan where the Gateway fronts the still-undivided hrb_chatbot_service
before any RAG split happens)."""

import httpx
from fastapi import Request, Response

from hrb_common.observability.circuit_breaker import CircuitBreaker, CircuitOpenError
from hrb_common.observability.logger import get_logger
from hrb_common.observability.request_context import new_request_id

logger = get_logger("gateway.forward")

# One breaker per backend base URL would be more precise once there are
# multiple real backends (Phase 3 extended) - one shared breaker is
# correct for this phase's single-backend scope.
_breaker = CircuitBreaker("gateway_backend", failure_threshold=2, cooldown_seconds=10)

# Headers Starlette/httpx should not forward verbatim between hops.
_EXCLUDED_REQUEST_HEADERS = {"host", "content-length"}
_EXCLUDED_RESPONSE_HEADERS = {"content-length", "transfer-encoding", "connection"}


class BackendUnavailableError(Exception):
    pass


async def forward_request(request: Request, backend_base_url: str, client: httpx.AsyncClient | None = None) -> Response:
    """Forwards method/path/query/body/headers unchanged except an added
    X-Request-ID; returns the backend's response unchanged - no reshaping,
    no aggregation (both explicitly out of scope, see ROADMAP.md)."""
    request_id = new_request_id()
    url = backend_base_url.rstrip("/") + request.url.path
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _EXCLUDED_REQUEST_HEADERS}
    headers["X-Request-ID"] = request_id
    body = await request.body()

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=30)

    try:
        try:
            with _breaker:
                backend_response = await client.request(
                    request.method, url, params=request.query_params, headers=headers, content=body
                )
        except CircuitOpenError as error:
            logger.warning("Forwarding skipped, circuit open: %s", error)
            raise BackendUnavailableError(str(error)) from error
        except httpx.HTTPError as error:
            logger.warning("Forwarding to %s failed: %s", url, error)
            raise BackendUnavailableError(str(error)) from error
    finally:
        if owns_client:
            await client.aclose()

    response_headers = {k: v for k, v in backend_response.headers.items() if k.lower() not in _EXCLUDED_RESPONSE_HEADERS}
    response_headers["X-Request-ID"] = request_id
    return Response(content=backend_response.content, status_code=backend_response.status_code, headers=response_headers)
