#!/bin/bash
set -e

if [ -z "$PROJECT_ID" ]; then
  echo "ERROR: Set your GCP project first: export PROJECT_ID=your-project-id"
  exit 1
fi

echo "Deploying Stage 1 (OCR)..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/stage1-ocr ./stage1_ocr
gcloud run deploy stage1-ocr \
  --image gcr.io/$PROJECT_ID/stage1-ocr \
  --memory 2Gi \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

echo "Deploying Stage 2 (Huffman)..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/stage2-huffman ./stage2_huffman
gcloud run deploy stage2-huffman \
  --image gcr.io/$PROJECT_ID/stage2-huffman \
  --memory 2Gi \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

echo ""
echo "Done! Set your env vars:"
echo "  export STAGE1_URL=\$(gcloud run services describe stage1-ocr --region us-central1 --format 'value(status.url)')"
echo "  export STAGE2_URL=\$(gcloud run services describe stage2-huffman --region us-central1 --format 'value(status.url)')"
