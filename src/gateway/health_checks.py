"""GET /health's real backend checks - modeled on hrb_chatbot_v2's own
api/admin/health_checks.py (each check returns {"status", "message"},
never raises; check_all() aggregates them into one overall status)."""

import httpx

from hrb_common.cache.connection import get_redis_client
from hrb_common.observability.secrets import read_secret

BACKEND_HEALTH_TIMEOUT_SECONDS = 10


def check_redis() -> dict:
    try:
        get_redis_client().ping()
        return {"status": "healthy", "message": "Redis reachable."}
    except Exception as error:
        return {"status": "unhealthy", "message": str(error)}


async def check_backend_service(backend_base_url: str, client: httpx.AsyncClient | None = None) -> dict:
    """Phase 7 - calls the forwarded backend's own GET /health (not /ping,
    Phase 6's original choice) and carries its full JSON body through as
    backend_report, so a caller (hrb_chatbot_ui's Settings -> Model tab)
    can read embedding_model/LLM/vector-store detail that only exists on
    the backend's own /health - Phase 6's /ping-only check had none of
    that. Real, known cost: this is now a real LLM-provider call every
    time this Gateway's own /health is checked, not a free ping - accepted
    deliberately (see ROADMAP.md Phase 7's Out of scope). Optional client
    param - same testability convention as routing/forward.py::forward_request."""
    url = backend_base_url.rstrip("/") + "/health"
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=BACKEND_HEALTH_TIMEOUT_SECONDS)
    try:
        try:
            response = await client.get(url)
        except httpx.HTTPError as error:
            return {"status": "unhealthy", "message": str(error), "backend_report": None}
        if response.status_code != 200:
            return {
                "status": "unhealthy",
                "message": f"Backend returned HTTP {response.status_code}.",
                "backend_report": None,
            }
        try:
            backend_report = response.json()
        except ValueError as error:
            return {"status": "unhealthy", "message": f"Backend returned non-JSON: {error}", "backend_report": None}
        return {"status": "healthy", "message": "Backend reachable.", "backend_report": backend_report}
    finally:
        if owns_client:
            await client.aclose()


async def check_all() -> dict:
    backend_base_url = read_secret("BACKEND_SERVICE_URL", "http://127.0.0.1:8093")
    checks = {
        "redis": check_redis(),
        "backend_service": await check_backend_service(backend_base_url),
    }
    overall_status = "healthy" if all(check["status"] == "healthy" for check in checks.values()) else "unhealthy"
    return {"status": overall_status, "checks": checks}
