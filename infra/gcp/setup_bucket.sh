#!/usr/bin/env bash
# Minimal gcloud-only bootstrap when Terraform is not used.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
DATA_BUCKET="${DATA_BUCKET:?unique bucket name}"
CKPT_BUCKET="${CKPT_BUCKET:?unique bucket name}"
SA_NAME="${SA_NAME:-jarvis-training}"

gcloud config set project "${PROJECT_ID}"

gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${DATA_BUCKET}" || true
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${CKPT_BUCKET}" || true

gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="Jarvis training" || true

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gsutil iam ch "serviceAccount:${SA_EMAIL}:objectAdmin" "gs://${DATA_BUCKET}"
gsutil iam ch "serviceAccount:${SA_EMAIL}:objectAdmin" "gs://${CKPT_BUCKET}"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user" || true

echo "Service account: ${SA_EMAIL}"
echo "gs://${DATA_BUCKET}"
echo "gs://${CKPT_BUCKET}"
