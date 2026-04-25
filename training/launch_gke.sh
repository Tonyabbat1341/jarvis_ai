#!/usr/bin/env bash
# Example Job manifest — apply a Kubernetes Job that runs distributed training (DeepSpeed launcher).
set -euo pipefail

kubectl apply -f "$(dirname "$0")/k8s/training_job.yaml"
