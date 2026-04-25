#!/usr/bin/env bash
# Soumet un Vertex AI Custom Job (Megatron + Jarvis dans l'image Docker).
# Les variables d'environnement sont passées via bash -c (gcloud n'a pas --env-vars sur custom-jobs create).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
IMAGE_URI="${IMAGE_URI:?container image in Artifact Registry}"
GCS_DATA="${GCS_DATA:?gs://bucket/data}"
GCS_CKPT="${GCS_CKPT:?gs://bucket/checkpoints}"

DISPLAY_NAME="${DISPLAY_NAME:-jarvis-mini-training}"
MACHINE_TYPE="${MACHINE_TYPE:-a2-highgpu-1g}"
REPLICA_COUNT="${REPLICA_COUNT:-1}"
ACCELERATOR_TYPE="${ACCELERATOR_TYPE:-NVIDIA_TESLA_A100}"
ACCELERATOR_COUNT="${ACCELERATOR_COUNT:-8}"

MODEL_CONFIG="${MODEL_CONFIG:-/workspace/jarvis/configs/model_jarvis_mini_1_0.yaml}"
TP="${TENSOR_MODEL_PARALLEL_SIZE:-2}"
PP="${PIPELINE_MODEL_PARALLEL_SIZE:-1}"
NPROC="${NPROC_PER_NODE:-${ACCELERATOR_COUNT}}"

# Pas de virgules dans cette chaîne : gcloud sépare --args par des virgules.
REMOTE_SCRIPT="export DATA_PATH='${GCS_DATA}';"
REMOTE_SCRIPT+="export CHECKPOINT_DIR='${GCS_CKPT}';"
REMOTE_SCRIPT+="export MODEL_CONFIG='${MODEL_CONFIG}';"
REMOTE_SCRIPT+="export TENSOR_MODEL_PARALLEL_SIZE='${TP}';"
REMOTE_SCRIPT+="export PIPELINE_MODEL_PARALLEL_SIZE='${PP}';"
REMOTE_SCRIPT+="export NPROC_PER_NODE='${NPROC}';"
REMOTE_SCRIPT+="export MEGATRON_ROOT='/workspace/Megatron-LM';"
REMOTE_SCRIPT+="export JARVIS_ROOT='/workspace/jarvis';"
REMOTE_SCRIPT+="cd /workspace/Megatron-LM && bash ../jarvis/training/megatron/run_pretrain.sh"

gcloud ai custom-jobs create \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --display-name="${DISPLAY_NAME}" \
  --worker-pool-spec="machine-type=${MACHINE_TYPE},replica-count=${REPLICA_COUNT},accelerator-type=${ACCELERATOR_TYPE},accelerator-count=${ACCELERATOR_COUNT},container-image-uri=${IMAGE_URI}" \
  --command=bash \
  --args=-c,"${REMOTE_SCRIPT}"
