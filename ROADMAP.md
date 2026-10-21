# hrb_api_gateway_service Roadmap

Phase-by-phase plan and history, same convention as `hrb_chatbot_v2`'s `docs/agent-reference/RAG-ROADMAP.md`.

## Status at a glance

| Phase | Title | Status | Spec |
|---|---|---|---|
| 1 | CORS + rate limit | ✅ Done | written |
| 2 | RBAC (absorb rbac.py) | ✅ Done | written |
| 3 | Route-to-service forwarding | ✅ Done (single-backend) | written |
| 4 | Contract validation | 📋 Planned | not yet written |
| 5 | Cutover - front hrb_chatbot_service | 📋 Planned | not yet written |

## Phases

- [x] **Phase 1 (done) — CORS + rate limit.** CORS policy matching `hrb_chatbot_v2`'s current `main.py` config. Redis-backed per-`employee_id` rate limiting (prerequisite: Redis live in production). Depends on `hrb-common-libs[observability,cache]`.
  - **Spec:**
    - **Context:** first real code in this repo. Everything downstream (Phase 2's RBAC, Phase 3's forwarding) sits behind this entry layer.
    - **Source:** CORS config is a direct port of `hrb_chatbot_v2`'s `main.py` (`allow_origins=["https://hrb-chatbot-ui.rvsree.dev"]`, `allow_origin_regex=r"http://localhost:\d+"`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`). Rate limiting is new code - no equivalent exists in `hrb_chatbot_v2` today (flagged in NFR-review discussion as "already broken at real scale").
    - **Request/response contract:** rate-limit rejection returns `429` with the existing `{"error": ..., "code": "RATE_LIMITED"}` shape (`hrb_chatbot_v2`'s own `error_codes.py`/`api/dependencies.py::json_error` convention, replicated here since this service doesn't depend on `hrb_chatbot_v2`'s own code).
    - **API surface:** `configure_cors(app)`, `RateLimiter(redis_client, limit_per_minute=60)` with `.check(employee_id) -> bool`, a FastAPI dependency `enforce_rate_limit` that 429s when `.check()` returns False, `GET /ping` (process-up, no backend calls - same two-tier health convention as `hrb_chatbot_v2`).
    - **Failure modes:** CORS rejection is the browser's own job (no server-side code needed beyond correct headers). Rate-limit check failing open if Redis itself is unreachable (never block all traffic because Redis hiccuped) - logged as a warning, not silently swallowed.
    - **Out of scope:** RBAC (Phase 2), routing (Phase 3), contract validation (Phase 4).
    - **Open questions:** none blocking.

- [x] **Phase 2 (done) — RBAC, absorbing rbac.py.** Port `require_role()`'s contract from `hrb_chatbot_v2`'s `api/gateway/rbac.py` - 401 if `user_profile` missing/invalid role, 403 if role not permitted on the route. Identity stays self-asserted (unsigned `user_profile` in the body) - real OAuth2 is a deliberately separate, later phase, not bundled here.
  - **Spec:**
    - **Context:** absorbing, not duplicating - once this is live, `hrb_chatbot_v2`'s `api/gateway/` package is deleted from the (split) backend repos, per the Decisions doc's own ruling. Two places checking the same role claim is how one of them goes stale.
    - **Source:** direct port of `hrb_chatbot_v2`'s `api/gateway/rbac.py::require_role()`/`identity_from_query_params()`, plus the `UserProfile` model (`models/common.py`) and `Role` enum (`common/enums.py`) it depends on - ported as this repo's own copies since it doesn't import `hrb_chatbot_v2`'s code.
    - **Request/response contract:** 401 if `user_profile` missing or its `role` isn't a real `Role` value; 403 if the role isn't one of the route's allowed roles. Identical status codes/detail-message shape to the original.
    - **API surface:** `UserProfile` (pydantic model), `Role` (StrEnum: employee/manager/hr_support/admin/employee_admin), `require_role(user_profile, *allowed_roles) -> UserProfile`, `identity_from_query_params(...)` for the three GET routes that can't carry a body (Fetch spec forbids it on GET/HEAD - same Phase 96 reasoning as the original).
    - **Behavior parity:** ported with no logic changes - same status codes, same detail-message shape.
    - **Out of scope:** real OAuth2/signed identity (unwired placeholder in `hrb_chatbot_v2` today, a deliberately separate later phase - see Decisions). Route-level wiring of `require_role()` into actual forwarded routes (Phase 3, once there's something to forward to).
    - **Open questions:** none blocking.

- [x] **Phase 3 (done, single-backend) — route-to-service forwarding.** Plain env-var URL map (`RAG_INGESTION_SERVICE_URL`, `RAG_RETRIEVAL_SERVICE_URL`, ...), same pattern as `HRB_LMS_MCP_URL`. Forwards request body/headers + adds `request_id`.
  - **Spec:**
    - **Context:** `rag_ingestion_service`/`rag_retrieval_service` don't exist yet - this phase builds generic forwarding against one configurable backend, so it can be proven against the still-undivided `hrb_chatbot_service` today (per the original cutover plan - Phase 5 points the real frontend at the Gateway, forwarding 1:1 to one backend, before any RAG split happens). The route-to-*multiple*-services map becomes real config once those services exist - the forwarding mechanism itself doesn't need to wait.
    - **Source:** new code. `request_id` generation reuses `hrb_common.observability`'s `new_request_id()`/`set_request_id()` from Phase 1 of `hrb-common-libs`.
    - **Request/response contract:** forwards method/path/query/body/headers unchanged except `X-Request-ID` added; returns the backend's response unchanged (status code, body, most headers) - no reshaping, no aggregation (explicitly out of scope per the Decisions doc).
    - **API surface:** `forward_request(request: Request, backend_base_url: str) -> Response` - a generic reverse-proxy function; `BACKEND_SERVICE_URL` env var for the single-backend case this phase actually covers.
    - **Failure modes:** backend unreachable → Resiliency's `CircuitBreaker` (from `hrb_common.observability`) trips after repeated failures → `503` with `{"error", "code": "BACKEND_UNAVAILABLE"}`, not a hung connection.
    - **Out of scope:** the real multi-service route map (Phase 3 extended, once `rag_ingestion_service`/`rag_retrieval_service` exist) - this phase proves the mechanism against one backend. Response aggregation across backends (still conditional on more backends existing, per the Decisions doc).
    - **Open questions:** none blocking.

- [ ] **Phase 4 (planned) — contract validation.** Validate outbound body against target backend's declared Pydantic schema before forwarding; 422 at the Gateway on mismatch.

- [ ] **Phase 5 (planned) — cutover.** Point `hrb_chatbot_ui` at this service; it forwards 1:1 to the still-undivided `hrb_chatbot_service`. Proves the Gateway before any RAG service split happens.
