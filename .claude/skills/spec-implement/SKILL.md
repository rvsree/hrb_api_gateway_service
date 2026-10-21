# Implement a spec'd phase

Execute one phase from `ROADMAP.md` that already has a written `**Spec:**`
block. Stay inside that spec's declared scope.

## Steps

1. Read the phase's `**Spec:**` block in full.
2. Implement under `src/gateway/`, following the request-validation
   pipeline order already fixed in CLAUDE.md (CORS → rate limit → RBAC →
   contract validation → route).
3. Write tests - fakes for Redis/downstream services, matching this
   project family's existing fake-based test pattern (no real network
   calls in tests).
4. Run `pytest -v` for the whole repo.
5. Flip the phase's checkbox to `- [x]` only after tests pass.
6. Produce a delivery note (`/delivery-note`).
