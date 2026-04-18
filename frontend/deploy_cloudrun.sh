#!/usr/bin/env bash
# Build and deploy the frontend (FastAPI proxy + static UI) to Google Cloud Run.
#
# Prereqs (one-time per machine):
#   gcloud auth login
#   gcloud config set project "$GCP_PROJECT_ID"
#   gcloud auth configure-docker "$REGION-docker.pkg.dev"   # only if pushing locally
#
# Prereqs (one-time per project):
#   gcloud services enable run.googleapis.com \
#                          cloudbuild.googleapis.com \
#                          artifactregistry.googleapis.com
#   gcloud artifacts repositories create "$REPO" \
#       --repository-format=docker --location="$REGION"
#
# Usage:
#   GCP_PROJECT_ID=my-project ./deploy_cloudrun.sh
#
# Tweak any of the env vars below to override defaults. In particular,
# STAGE1_URL / STAGE2_URL must point at the deployed Cloud Run services
# for /api/ocr and /api/compress* / /api/decompress to work.

set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID to your GCP project, e.g. export GCP_PROJECT_ID=my-project}"

REGION="${REGION:-us-central1}"
REPO="${REPO:-crisp}"
SERVICE="${SERVICE:-frontend}"
IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/${SERVICE}"
TAG="${TAG:-$(date -u +%Y%m%d-%H%M%S)}"

# Backend service URLs the frontend proxies to. Override at deploy time if
# the stage1/stage2 services move or you spin up a separate environment.
STAGE1_URL="${STAGE1_URL}"
STAGE2_URL="${STAGE2_URL}"

# Resource sizing — pure-Python httpx proxy + static file serving. Very light;
# 1 CPU / 512 MiB handles plenty of concurrent requests since each handler is
# just an async forward to stage1/stage2.
CPU="${CPU:-1}"
MEMORY="${MEMORY:-512Mi}"
CONCURRENCY="${CONCURRENCY:-80}"
TIMEOUT="${TIMEOUT:-120}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-3}"

cd "$(dirname "$0")"

echo ">> Building image with Cloud Build: ${IMAGE}:${TAG}"
gcloud builds submit \
    --project "${GCP_PROJECT_ID}" \
    --tag "${IMAGE}:${TAG}" \
    .

echo ">> Deploying to Cloud Run: ${SERVICE} (${REGION})"
gcloud run deploy "${SERVICE}" \
    --project "${GCP_PROJECT_ID}" \
    --region "${REGION}" \
    --image "${IMAGE}:${TAG}" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --cpu "${CPU}" \
    --memory "${MEMORY}" \
    --concurrency "${CONCURRENCY}" \
    --timeout "${TIMEOUT}" \
    --min-instances "${MIN_INSTANCES}" \
    --max-instances "${MAX_INSTANCES}" \
    --cpu-boost \
    --set-env-vars "STAGE1_URL=${STAGE1_URL},STAGE2_URL=${STAGE2_URL}"

echo ">> Done. Service URL:"
gcloud run services describe "${SERVICE}" \
    --project "${GCP_PROJECT_ID}" \
    --region "${REGION}" \
    --format='value(status.url)'
