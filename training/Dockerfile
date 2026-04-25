# Training image: Jarvis + Megatron-LM (branche pinnée) pour pré-entraînement GCP.
# Build: docker build -f training/Dockerfile -t REGION-docker.pkg.dev/PROJECT/jarvis/train:tag .
# Surcharges utiles: --build-arg MEGATRON_REF=core_r0.12.0 --build-arg PY_ENV=pytorch_24.01

# 2.2.x images ship Python 3.10; pyproject requires >=3.11. 2.4.x cuda12.1 runtime uses Python 3.11.
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/jarvis
COPY pyproject.toml README.md ./
COPY src ./src
COPY training ./training
COPY configs ./configs
COPY data ./data

RUN pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir -e ".[training]"

# Megatron-LM — même branche que celle testée avec les flags de jarvis_yaml_to_args.py
ARG MEGATRON_REF=core_r0.12.0
ARG PY_ENV=pytorch_24.01
ENV PY_ENV=${PY_ENV}
ENV MEGATRON_ROOT=/workspace/Megatron-LM
ENV JARVIS_ROOT=/workspace/jarvis

RUN git clone --single-branch --depth 1 --branch "${MEGATRON_REF}" \
      https://github.com/NVIDIA/Megatron-LM.git /workspace/Megatron-LM \
    && pip install --no-cache-dir -e /workspace/Megatron-LM

WORKDIR /workspace/jarvis
ENV PYTHONUNBUFFERED=1
CMD ["python", "training/train_tiny_gpt.py", "--help"]
