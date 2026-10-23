"""Consistent error shape - same convention as hrb_chatbot_v2's api/dependencies.py::json_error."""

from fastapi.responses import JSONResponse


def json_error(status_code: int, message: str, code: str, headers: dict | None = None, **extra) -> JSONResponse:
    body = {"error": message, "code": code}
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def health_response(report: dict) -> JSONResponse:
    """Phase 6 - same convention as hrb_chatbot_v2's api/dependencies.py::health_response:
    200 when every check is healthy, 503 otherwise."""
    status_code = 200 if report["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=report)
