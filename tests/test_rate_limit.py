import fakeredis
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from gateway.error_codes import RATE_LIMITED
from gateway.middleware.rate_limit import RateLimitExceeded, RateLimiter, enforce_rate_limit
from gateway.responses import json_error


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


def test_allows_requests_under_the_limit(fake_redis):
    limiter = RateLimiter(redis_client=fake_redis, limit_per_minute=3)
    assert limiter.check("EMP051") is True
    assert limiter.check("EMP051") is True
    assert limiter.check("EMP051") is True


def test_blocks_requests_over_the_limit(fake_redis):
    limiter = RateLimiter(redis_client=fake_redis, limit_per_minute=2)
    assert limiter.check("EMP051") is True
    assert limiter.check("EMP051") is True
    assert limiter.check("EMP051") is False


def test_different_identities_have_independent_limits(fake_redis):
    limiter = RateLimiter(redis_client=fake_redis, limit_per_minute=1)
    assert limiter.check("EMP051") is True
    assert limiter.check("EMP052") is True  # a different employee, not blocked by EMP051's count


def test_fails_open_when_redis_is_unreachable():
    class BrokenRedis:
        def incr(self, key):
            raise ConnectionError("redis down")

    limiter = RateLimiter(redis_client=BrokenRedis())
    assert limiter.check("EMP051") is True  # never block traffic because Redis hiccuped


def test_dependency_rejects_with_429_over_limit(fake_redis):
    app = FastAPI()
    limiter = RateLimiter(redis_client=fake_redis, limit_per_minute=1)

    @app.exception_handler(RateLimitExceeded)
    async def handler(request, exc):
        return json_error(429, "Too many requests", RATE_LIMITED, headers={"Retry-After": str(exc.retry_after_seconds)})

    @app.post("/protected", dependencies=[Depends(enforce_rate_limit(limiter))])
    async def protected():
        return {"ok": True}

    client = TestClient(app)
    body = {"user_profile": {"employee_id": "EMP051"}}

    first = client.post("/protected", json=body)
    assert first.status_code == 200

    second = client.post("/protected", json=body)
    assert second.status_code == 429
    assert second.json()["code"] == RATE_LIMITED
