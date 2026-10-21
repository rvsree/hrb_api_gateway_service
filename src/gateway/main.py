from fastapi import FastAPI, Request

from gateway.error_codes import RATE_LIMITED
from gateway.middleware.cors import configure_cors
from gateway.middleware.rate_limit import RateLimitExceeded, RateLimiter, enforce_rate_limit
from gateway.responses import json_error

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


@app.get("/ping")
async def ping():
    """Process-is-up only, no backend calls - same two-tier health convention as hrb_chatbot_v2."""
    return {"status": "ok"}
