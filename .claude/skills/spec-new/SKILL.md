# Write a new spec

A spec is a `**Spec:**` block written into the target phase's own bullet
in `ROADMAP.md`'s `## Phases` section, **before** that phase's code starts.

## Steps

1. Find the target phase's `- [ ]` bullet in `ROADMAP.md`'s `## Phases` section.
2. Append a nested `**Spec:**` sub-list:

   ```
   - **Spec:**
     - **Context:** why this phase, what triggered it.
     - **Request/response contract** (if this phase touches an endpoint):
       confirm the shape here, or point at hrb_chatbot_v2's
       endpoint-request-response-contracts.md for the backend route being
       fronted.
     - **Failure modes:** what's expected to go wrong, what the Gateway
       returns for each (status code + error code).
     - **Out of scope:** what this phase deliberately does not do.
     - **Open questions:** anything needing a decision before/during implementation.
   ```

3. Set the phase's checkbox to `- [ ]` if not already.
4. No implementation code in this step - report the spec for review first.
