# hrb_api_gateway_service

The single public entry point for the HRB chatbot system - RBAC, CORS, rate-limiting, and contract validation, centralized once for every backend service it fronts.

Full design doc: `hrb_chatbot_service`'s `docs/dev-reference/api-gateway-service/` and `docs/dev-reference/service-boundary-decision.html`.

**Status, 2026-10-23: live in production.** Deployed to AWS App Runner (`https://necxf9n7mv.us-east-1.awsapprunner.com`), and `hrb_chatbot_ui` is cut over to call it instead of the backend directly - confirmed with a real CORS preflight and a real forwarded `genai-rag-retrieval` query. CORS, rate-limiting (Redis-backed, shared across replicas), contract validation, and `api/gateway/rbac.py`'s own RBAC role absorbed into this service are all built. See `ROADMAP.md` for phase history - one real bug found and fixed along the way: the forwarder's client timeout (30s) was too short for a real `~60s` agentic query and tripped its own circuit breaker on genuinely-slow-not-failed backend calls, now `90s`.
