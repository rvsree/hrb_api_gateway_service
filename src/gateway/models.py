"""UserProfile - ported from hrb_chatbot_v2's models/common.py, same shape.
Self-asserted identity - see rbac.py's module docstring and ROADMAP.md's
Phase 2 Decisions note on why this isn't upgraded to real auth here."""

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    employee_id: str = Field(..., max_length=50)
    full_name: str = Field(..., max_length=200)
    role: str = Field(..., max_length=50)
    department: str | None = Field(None, max_length=100)
