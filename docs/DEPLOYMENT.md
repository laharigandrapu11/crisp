# GCP Cloud Run Deployment

## Prerequisites
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- Logged in: `gcloud auth login`
- Project set: `gcloud config set project <PROJECT_ID>`
- Container Registry enabled: `gcloud services enable containerregistry.googleapis.com run.googleapis.com`

---

## Deploy Stage 1 — OCR Service

```bash
# Build and push image
gcloud builds submit --tag gcr.io/<PROJECT_ID>/stage1-ocr ./stage1_ocr

# Deploy to Cloud Run (2Gi memory required for PyTorch)
gcloud run deploy stage1-ocr \
  --image gcr.io/<PROJECT_ID>/stage1-ocr \
  --memory 2Gi \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Deploy Stage 2 — Huffman Compression Service

```bash
# Build and push image
gcloud builds submit --tag gcr.io/<PROJECT_ID>/stage2-huffman ./stage2_huffman

# Deploy to Cloud Run
gcloud run deploy stage2-huffman \
  --image gcr.io/<PROJECT_ID>/stage2-huffman \
  --memory 2Gi \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## After Deploying

Set the service URLs as environment variables before running the pipeline:

```bash
export STAGE1_URL=https://stage1-ocr-<hash>.run.app
export STAGE2_URL=https://stage2-huffman-<hash>.run.app

python3 integration/pipeline.py <image_path>
```

---

## Health Checks

Verify both services are up before running the pipeline:

```bash
curl $STAGE1_URL/health
curl $STAGE2_URL/health
```

Both should return `{"status": "ok"}`.
