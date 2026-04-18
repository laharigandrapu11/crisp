#!/usr/bin/env bash
# Build and deploy stage2_huffman to Google Cloud Run.
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
# Tweak any of the env vars below to override defaults.

set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID to your GCP project, e.g. export GCP_PROJECT_ID=my-project}"

REGION="${REGION:-us-central1}"
REPO="${REPO:-crisp}"
SERVICE="${SERVICE:-stage2-huffman}"
IMAGE="${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/${SERVICE}"
TAG="${TAG:-$(date -u +%Y%m%d-%H%M%S)}"

# Resource sizing — Stage 2 is pure-Python adaptive Huffman with no model
# weights and no native deps beyond CPython. 1 CPU / 512 MiB is plenty for
# typical text payloads; bump CPU/memory if you compress very large blobs.
CPU="${CPU:-1}"
MEMORY="${MEMORY:-512Mi}"
CONCURRENCY="${CONCURRENCY:-40}"
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
    --cpu-boost

echo ">> Done. Service URL:"
gcloud run services describe "${SERVICE}" \
    --project "${GCP_PROJECT_ID}" \
    --region "${REGION}" \
    --format='value(status.url)'
