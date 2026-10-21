# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The single public entry point for the HRB chatbot system's browser traffic - session/identity validation (RBAC), CORS, rate-limiting, and request/response contract validation, centralized once instead of duplicated across every backend service it fronts.

Full design (purpose, scope, request-validation pipeline, failure paths, the `rbac.py`-absorption decision, KPIs) lives in `hrb_chatbot_v2`'s own `docs/dev-reference/api-gateway-service/` doc set (Overview/Spec/Architecture/Design/Decisions) - read that before changing anything here. This repo implements that design; it doesn't re-derive it.

Python 3.12, FastAPI - matches every other service in this system.

## Commands

```bash
# install
pip install -r requirements.txt

# run (local dev)
uvicorn src.gateway.main:app --reload --port 8100

# test
pytest -v
```

## Architecture

Request pipeline, each stage able to short-circuit the rest (cheapest/least-trusted checks first): **CORS check** → **rate limit check** (Redis-backed, holds across replicas) → **identity/RBAC** (same contract as `hrb_chatbot_v2`'s `require_role()`) → **contract validation** (against the target backend's declared schema) → **route to backend** (by path prefix, via a plain env-var URL map - same pattern already proven for `HRB_LMS_MCP_URL`).

No business data, no Postgres schema of its own - rate-limit/session state lives in Redis only. See the Design tab for the full route-to-service map, `requirements.txt`, and `.env.example`.

This service never aggregates responses across backends (that's classic BFF behavior) until there are enough real backend services behind it to make aggregation worth it - see the Decisions tab.

## Spec-Driven Development

Same convention as `hrb_chatbot_v2`: a spec is a `**Spec:**` block in `ROADMAP.md`'s `## Phases` section, written before that phase's code starts. `.claude/scripts/spec_gate.py` blocks a `Write`/`Edit` under `src/gateway/**` unless `ROADMAP.md` has an open, spec'd phase.

**Four working norms:**
- **One task at a time.**
- **Flag, don't fix.**
- **Nothing gets pushed without the user's own review and explicit go-ahead first.**
- **This service absorbs `hrb_chatbot_v2`'s `api/gateway/rbac.py` - it does not duplicate it.** Once this service is live, that package gets deleted from the (split) backend repos, not kept as a second enforcement point.

**Available skills**: `session-start`, `delivery-note`, `spec-new`, `spec-implement`.
**Subagents**: `.claude/agents/implementer.md`, `.claude/agents/code-reviewer.md`.
