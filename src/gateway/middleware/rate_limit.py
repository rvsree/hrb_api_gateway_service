"""Redis-backed per-employee rate limiting - new code, no equivalent exists in
hrb_chatbot_v2 today (flagged in the NFR review as "already broken at real scale").
Fixed-window counter via INCR+EXPIRE - simple, good enough for this traffic level;
a sliding window is a straightforward later upgrade if the fixed-window edge
(a burst straddling two windows) ever actually matters in practice."""

from fastapi import HTTPException, Request

from hrb_common.cache.connection import build_cache_key, get_redis_client
from hrb_common.observability.logger import get_logger

logger = get_logger("gateway.rate_limit")

DEFAULT_LIMIT_PER_MINUTE = 60
WINDOW_SECONDS = 60


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after_seconds: int):
        super().__init__(status_code=429, detail="Too many requests")
        self.retry_after_seconds = retry_after_seconds


class RateLimiter:
    def __init__(self, redis_client=None, limit_per_minute: int = DEFAULT_LIMIT_PER_MINUTE):
        self.redis_client = redis_client or get_redis_client()
        self.limit_per_minute = limit_per_minute

    def check(self, identity: str) -> bool:
        """Returns True if this request is allowed, False if the limit is exceeded.
        Fails open (allows the request) if Redis itself is unreachable - a rate
        limiter must never become the reason every request fails."""
        key = build_cache_key("api_gateway_service", "rate_limit", identity)
        try:
            count = self.redis_client.incr(key)
            if count == 1:
                self.redis_client.expire(key, WINDOW_SECONDS)
            return count <= self.limit_per_minute
        except Exception as error:
            logger.warning("Rate limiter could not reach Redis, failing open: %s", error)
            return True


async def _extract_identity(request: Request) -> str:
    """employee_id from user_profile if the body has one (the established self-
    asserted identity contract), else the client's IP - never raises on a
    malformed body, since rate limiting must never be the thing that crashes a request."""
    try:
        body = await request.json()
        employee_id = (body.get("user_profile") or {}).get("employee_id")
        if employee_id:
            return str(employee_id)
    except Exception:
        pass
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(limiter: RateLimiter):
    """FastAPI dependency factory - bind one RateLimiter instance per app, not per request."""

    async def _dependency(request: Request) -> None:
        identity = await _extract_identity(request)
        if not limiter.check(identity):
            raise RateLimitExceeded(retry_after_seconds=WINDOW_SECONDS)

    return _dependency
