#!/usr/bin/env bash
# Variables GCS alignées sur le PROJECT_ID (à sourcer depuis Cloud Shell après export PROJECT_ID).
# Usage : export PROJECT_ID="ton-projet-id" ; source infra/gcp/cloudshell_env.sh
# Tu peux surcharger BUCKET_DATA / BUCKET_CKPT avant le source si le nom par défaut est déjà pris mondialement.

if [[ -z "${PROJECT_ID:-}" ]]; then
  PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
fi
if [[ -z "${PROJECT_ID:-}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "cloudshell_env.sh : définis PROJECT_ID ou gcloud config set project ..." >&2
  return 1 2>/dev/null || exit 1
fi

REGION="${REGION:-us-central1}"
export REGION
export PROJECT_ID

export BUCKET_DATA="${BUCKET_DATA:-${PROJECT_ID}-jarvis-data}"
export BUCKET_CKPT="${BUCKET_CKPT:-${PROJECT_ID}-jarvis-ckpt}"
export GCS_DATA="${GCS_DATA:-gs://${BUCKET_DATA}/jarvis/megatron_data}"
export GCS_CKPT="${GCS_CKPT:-gs://${BUCKET_CKPT}/jarvis/runs/mini-1}"
