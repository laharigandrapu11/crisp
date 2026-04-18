# syntax=docker/dockerfile:1.7

# ---------- builder ----------
# Install Python deps in a venv so the final image only contains what we need.
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# ---------- runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# Pure-Python proxy + static file server, so no system libs needed beyond
# what python:slim ships. Just create the non-root user we'll run as.
RUN useradd --create-home --uid 1001 app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . /app

USER app

EXPOSE 8080

# Cloud Run injects $PORT. Single worker — Cloud Run scales by spawning more
# container instances, not workers.
CMD exec uvicorn server:app --host 0.0.0.0 --port "${PORT}" --workers 1
