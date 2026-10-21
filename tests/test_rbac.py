"""Tests for require_role()/identity_from_query_params() - ported from
hrb_chatbot_v2's tests/hrb_chatbot/api/gateway/test_rbac.py for behavior parity."""

import pytest
from fastapi import HTTPException

from gateway.enums import Role
from gateway.models import UserProfile
from gateway.rbac import identity_from_query_params, require_role


def test_missing_user_profile_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        require_role(None, Role.HR_SUPPORT)
    assert exc_info.value.status_code == 401


def test_unknown_role_raises_401():
    profile = UserProfile(employee_id="EMP052", full_name="Eddy Employee", role="made-up-role")
    with pytest.raises(HTTPException) as exc_info:
        require_role(profile, Role.HR_SUPPORT)
    assert exc_info.value.status_code == 401


def test_valid_identity_wrong_role_raises_403():
    profile = UserProfile(employee_id="EMP052", full_name="Eddy Employee", role="employee")
    with pytest.raises(HTTPException) as exc_info:
        require_role(profile, Role.HR_SUPPORT)
    assert exc_info.value.status_code == 403


def test_valid_identity_allowed_role_returns_the_user_profile():
    profile = UserProfile(employee_id="EMP051", full_name="Hana Support", role="hr_support")
    result = require_role(profile, Role.HR_SUPPORT)
    assert result is profile


def test_identity_from_query_params_builds_profile_when_all_present():
    profile = identity_from_query_params(employee_id="EMP051", full_name="Hana Support", role="hr_support")
    assert profile.employee_id == "EMP051"


def test_identity_from_query_params_returns_none_when_any_missing():
    assert identity_from_query_params(employee_id="EMP051", full_name=None, role="hr_support") is None
