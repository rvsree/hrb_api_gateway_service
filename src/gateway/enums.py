"""Role - ported from hrb_chatbot_v2's common/enums.py::Role, same values.
This repo keeps its own copy rather than importing hrb_chatbot_v2's code -
once the split lands, this IS the one definition RBAC is checked against."""

from enum import StrEnum


class Role(StrEnum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR_SUPPORT = "hr_support"
    ADMIN = "admin"
    EMPLOYEE_ADMIN = "employee_admin"
