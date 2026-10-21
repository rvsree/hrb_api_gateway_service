from fastapi import Depends, FastAPI, Request

from gateway.error_codes import BACKEND_UNAVAILABLE, RATE_LIMITED
from gateway.middleware.cors import configure_cors
from gateway.middleware.rate_limit import RateLimitExceeded, RateLimiter, enforce_rate_limit
from gateway.responses import json_error
from gateway.routing.forward import BackendUnavailableError, forward_request
from hrb_common.observability.secrets import read_secret

app = FastAPI(
    title="HRB API Gateway",
    version="0.1.0",
    description="Single public entry point for the HRB chatbot system - RBAC, CORS, rate-limiting, contract validation.",
)

configure_cors(app)

_rate_limiter = RateLimiter()


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return json_error(
        status_code=429,
        message="Too many requests - try again shortly.",
        code=RATE_LIMITED,
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@app.exception_handler(BackendUnavailableError)
async def backend_unavailable_handler(request: Request, exc: BackendUnavailableError):
    return json_error(status_code=503, message="The backend service is currently unavailable.", code=BACKEND_UNAVAILABLE)


@app.get("/ping")
async def ping():
    """Process-is-up only, no backend calls - same two-tier health convention as hrb_chatbot_v2."""
    return {"status": "ok"}


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], dependencies=[Depends(enforce_rate_limit(_rate_limiter))])
async def forward_to_backend(path: str, request: Request):
    """Phase 3's single-backend forwarding - see ROADMAP.md. Role-based routing
    (which roles are allowed on which forwarded path) is deferred to once the
    real multi-service route map exists (Phase 3 extended) - a generic catch-all
    proxy has no per-path role mapping to enforce yet."""
    backend_base_url = read_secret("BACKEND_SERVICE_URL", "http://127.0.0.1:8093")
    return await forward_request(request, backend_base_url)
