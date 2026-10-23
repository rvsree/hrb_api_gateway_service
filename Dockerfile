# The HRB API Gateway, as a container image.
#
# Build it from the REPOSITORY ROOT, not from anywhere else:
#
#     docker build -t hrb-api-gateway-service:local .
#
# The build context has to be the repository root, because that is where
# requirements.txt and src/ live.
#
# Two stages, same shape as hrb_chatbot_service's own Dockerfile - but
# genuinely simpler: no spacy/presidio model download (this service has no
# PII-masking guardrail), no data/ directory permissions dance (this
# service is stateless - "no business data, no Postgres schema of its own,"
# per this repo's own CLAUDE.md).

# ---------------------------------------------------------------------------
# Stage 1 - build the virtual environment
# ---------------------------------------------------------------------------
# 3.12, matching every other service in this system.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# git is needed here only because requirements.txt pins hrb-common-libs via
# a git+https URL (not a published PyPI package) - pip needs it to clone
# that tag at install time.
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Requirements are copied on their own, before the source, so an ordinary
# code edit reuses Docker's cached install layer instead of reinstalling
# everything.
COPY requirements.txt ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 - the image that actually runs
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8100

# curl is for the HEALTHCHECK below - without it the health check can never pass.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Run as a normal user - nothing here needs root.
RUN useradd --create-home --uid 10001 hrbgateway

COPY --from=builder /opt/venv /opt/venv

# /srv holds src/ so imports written as `from src.gateway...` resolve the
# same way they do when running locally from the repository root. No .env
# is copied in: a container is configured through environment variables at
# run time, not a file baked into the image.
WORKDIR /srv
COPY --chown=hrbgateway:hrbgateway src ./src

USER hrbgateway

EXPOSE 8100

# GET /ping only confirms the process is up - no provider is called, no
# tokens spent. A probe running every 30 seconds forever must never be able
# to cost money or fail because a backend (not this container) is down -
# that's what GET /health is for, checked deliberately by hand, not by this probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8100/ping || exit 1

# No --reload here - reload runs the app in a child process, which breaks
# both container signal handling and any attached debugger.
#
# --app-dir src, not `src.gateway.main:app` (unlike hrb_chatbot_service's
# own `from src.hrb_chatbot...` convention) - this repo's own src/gateway/
# modules import each other as bare `from gateway import ...`, confirmed by
# a real local container run that failed with `ModuleNotFoundError: No
# module named 'gateway'` until this was fixed, not assumed from reading
# CLAUDE.md's own (stale) documented run command.
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8100", "--app-dir", "src"]
