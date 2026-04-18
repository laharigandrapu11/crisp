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

# Cloud Run is CPU-only; install the CPU wheels of torch/torchvision from
# the official PyTorch CPU index instead of the default CUDA build.
# Also swap opencv-python -> opencv-python-headless so we don't drag in GUI libs.
RUN sed -E -e 's/^torch==.*/torch==2.11.0/' \
           -e 's/^torchvision==.*/torchvision==0.26.0/' \
           -e 's/^opencv-python(\b|>=).*/opencv-python-headless>=4.10/' \
           requirements.txt > requirements.cloud.txt \
 && pip install --upgrade pip \
 && pip install --extra-index-url https://download.pytorch.org/whl/cpu \
                -r requirements.cloud.txt

# ---------- runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# libglib2.0-0 is needed by opencv-python-headless at runtime.
# Also create the non-root user we'll run as.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1001 app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . /app

USER app

EXPOSE 8080

# Cloud Run injects $PORT. Use a single worker — the model caches are per-process
# and Cloud Run scales by spawning more container instances, not workers.
CMD exec uvicorn main:app --host 0.0.0.0 --port "${PORT}" --workers 1
