#!/usr/bin/env bash
# Variables de session Jarvis Mini (Cloud Shell)
# Usage:
#   cd ~/jarvis_ai
#   source infra/gcp/jarvis_session_env.sh

export PROJECT_ID="onyx-parser-493701-c9"
export REGION="us-central1"

# Buckets / prefixes
export BUCKET_DATA="onyx-parser-493701-c9-jarvis-data"
export BUCKET_CKPT="onyx-parser-493701-c9-jarvis-ckpt"
export GCS_DATA="gs://${BUCKET_DATA}/jarvis/megatron_data"
export GCS_CKPT="gs://${BUCKET_CKPT}/jarvis/runs/mini-1"

# Image d'entraînement (Artifact Registry)
export IMAGE_URI="us-central1-docker.pkg.dev/onyx-parser-493701-c9/jarvis/train:jarvis-mini-20260425"

# Optionnel: se placer automatiquement sur le bon projet gcloud
gcloud config set project "${PROJECT_ID}" >/dev/null
