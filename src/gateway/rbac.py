"""Identity + role check for every forwarded route - ported from hrb_chatbot_v2's
api/gateway/rbac.py. 401 for a missing/invalid identity, 403 for the wrong role.

Absorbed, not duplicated: once this service is live, hrb_chatbot_v2's own
api/gateway/ package gets deleted from the (split) backend repos - see
ROADMAP.md's Phase 2 Decisions note. Identity stays self-asserted (unsigned
user_profile in the request body) - real OAuth2 is a deliberately separate,
later phase, not bundled into this one."""

from fastapi import HTTPException, Query

from gateway.enums import Role
from gateway.models import UserProfile


def identity_from_query_params(
    employee_id: str | None = Query(None),
    full_name: str | None = Query(None),
    role: str | None = Query(None),
) -> UserProfile | None:
    """For GET routes once forwarded (Phase 96's reasoning in hrb_chatbot_v2:
    the Fetch spec forbids a body on GET/HEAD) - returns None, not a 422,
    when anything's missing, so require_role() still raises its normal 401."""
    if employee_id is None or full_name is None or role is None:
        return None
    return UserProfile(employee_id=employee_id, full_name=full_name, role=role)


def require_role(user_profile: UserProfile | None, *allowed_roles: Role) -> UserProfile:
    if user_profile is None:
        raise HTTPException(status_code=401, detail="Missing required user_profile in the request payload")

    try:
        Role(user_profile.role)
    except ValueError:
        valid_roles = [member.value for member in Role]
        raise HTTPException(status_code=401, detail=f"Unknown role {user_profile.role!r} - choose one of {valid_roles}")

    if user_profile.role not in allowed_roles:
        allowed = [role.value for role in allowed_roles]
        raise HTTPException(
            status_code=403,
            detail=f"Role {user_profile.role!r} is not permitted here - requires one of {allowed}",
        )
    return user_profile
