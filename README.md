# hrb-api_gateway_service

The single public entry point for the HRB chatbot system - RBAC, CORS, rate-limiting, and contract validation, centralized once for every backend service it fronts.

Full design doc: `hrb_chatbot_v2`'s `docs/dev-reference/api-gateway-service/`.

Status: scaffolding only - no implementation yet. See `ROADMAP.md`. First real dependency: `hrb-common-libs[observability,db,cache,auth]`, and Redis live in production (rate-limiting needs shared state across replicas).
