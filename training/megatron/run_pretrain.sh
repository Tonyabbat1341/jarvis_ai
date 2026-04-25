#!/usr/bin/env bash
# Lance Megatron pretrain_gpt.py avec hyperparamètres issus du YAML Jarvis (MODEL_CONFIG).
# Prérequis : Megatron-LM installé (voir training/Dockerfile), données au format Megatron sur DATA_PATH.
set -euo pipefail

MEGATRON_ROOT="${MEGATRON_ROOT:-/workspace/Megatron-LM}"
JARVIS_ROOT="${JARVIS_ROOT:-/workspace/jarvis}"
MODEL_CONFIG="${MODEL_CONFIG:-${JARVIS_ROOT}/configs/model_jarvis_mini_1_0.yaml}"
DATA_PATH="${DATA_PATH:?DATA_PATH (ex. gs://bucket/prefix ou chemin local Megatron)}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:?CHECKPOINT_DIR}"

TP="${TENSOR_MODEL_PARALLEL_SIZE:-2}"
PP="${PIPELINE_MODEL_PARALLEL_SIZE:-1}"
DATA_SPLIT="${DATA_SPLIT:-949,50,1}"
DISTRIBUTED_BACKEND="${DISTRIBUTED_BACKEND:-nccl}"

TOKENIZER_TYPE="${TOKENIZER_TYPE:-HuggingFaceTokenizer}"
TOKENIZER_MODEL="${TOKENIZER_MODEL:-gpt2}"

if [[ ! -f "${MEGATRON_ROOT}/pretrain_gpt.py" ]]; then
  echo "Megatron pretrain_gpt.py introuvable : ${MEGATRON_ROOT}/pretrain_gpt.py" >&2
  exit 1
fi

if [[ ! -f "${MODEL_CONFIG}" ]]; then
  echo "MODEL_CONFIG introuvable : ${MODEL_CONFIG}" >&2
  exit 1
fi

mapfile -t MODEL_ARGS < <(python "${JARVIS_ROOT}/training/megatron/jarvis_yaml_to_args.py" "${MODEL_CONFIG}")

NP="${NPROC_PER_NODE:-}"
if [[ -z "${NP}" ]]; then
  NP="$(nvidia-smi -L 2>/dev/null | wc -l | tr -d ' ')"
fi
if [[ -z "${NP}" || "${NP}" == "0" ]]; then
  NP=1
fi

cd "${MEGATRON_ROOT}"

exec torchrun \
  --nproc_per_node="${NP}" \
  --nnodes="${NNODES:-1}" \
  --node_rank="${NODE_RANK:-0}" \
  --master_addr="${MASTER_ADDR:-127.0.0.1}" \
  --master_port="${MASTER_PORT:-29500}" \
  pretrain_gpt.py \
  "${MODEL_ARGS[@]}" \
  --tensor-model-parallel-size "${TP}" \
  --pipeline-model-parallel-size "${PP}" \
  --distributed-backend "${DISTRIBUTED_BACKEND}" \
  --data-path "${DATA_PATH}" \
  --split "${DATA_SPLIT}" \
  --save "${CHECKPOINT_DIR}" \
  --load "${CHECKPOINT_DIR}" \
  --tokenizer-type "${TOKENIZER_TYPE}" \
  --tokenizer-model "${TOKENIZER_MODEL}" \
  "$@"
