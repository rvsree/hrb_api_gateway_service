"""CORS policy - direct port of hrb_chatbot_v2's main.py config (Phase 95/167)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGIN = "https://hrb-chatbot-ui.rvsree.dev"
LOCALHOST_ORIGIN_REGEX = r"http://localhost:\d+"


def configure_cors(app: FastAPI) -> None:
    """No cookie-based session exists to protect against CSRF, so allow_credentials is safe here -
    same reasoning as hrb_chatbot_v2's own comment on this exact config."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ALLOWED_ORIGIN],
        allow_origin_regex=LOCALHOST_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
