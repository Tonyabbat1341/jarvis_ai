#!/usr/bin/env bash
# Construit l'image d'entraînement via Cloud Build (sans Docker local).
# À lancer depuis n'importe quel répertoire : le script se place à la racine du dépôt.
#
# Prérequis :
#   export PROJECT_ID="ton-projet"
#   export REGION="us-central1"
#
# Usage :
#   chmod +x infra/gcp/submit_train_image.sh   # une fois, dans Cloud Shell
#   bash infra/gcp/submit_train_image.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CLOUDBUILD="${REPO_ROOT}/infra/gcp/cloudbuild_jarvis_train.yaml"

cd "${REPO_ROOT}"

if [[ ! -f "${REPO_ROOT}/pyproject.toml" ]] || [[ ! -f "${REPO_ROOT}/training/Dockerfile" ]]; then
  echo "Erreur : ce script ne trouve pas la racine du projet (pyproject.toml + training/Dockerfile)." >&2
  echo "Répertoire déduit : ${REPO_ROOT}" >&2
  exit 1
fi

if [[ ! -f "${CLOUDBUILD}" ]]; then
  echo "Fichiers Cloud Build manquants — exécution du bootstrap…" >&2
  if [[ -f "${SCRIPT_DIR}/bootstrap_cloudbuild_assets.sh" ]]; then
    bash "${SCRIPT_DIR}/bootstrap_cloudbuild_assets.sh"
  else
    echo "Erreur : fichier manquant — ${CLOUDBUILD}" >&2
    echo "Lance depuis la racine du dépôt : bash infra/gcp/bootstrap_cloudbuild_assets.sh" >&2
    echo "(ou recrée ton ZIP en incluant infra/gcp/)." >&2
    exit 1
  fi
fi
if [[ ! -f "${CLOUDBUILD}" ]]; then
  echo "Erreur : ${CLOUDBUILD} toujours absent après bootstrap." >&2
  exit 1
fi

: "${PROJECT_ID:?Définis PROJECT_ID, ex. : export PROJECT_ID=mon-projet-id}"
: "${REGION:?Définis REGION, ex. : export REGION=us-central1}"

IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/jarvis/train:jarvis-mini-$(date +%Y%m%d)"
export IMAGE_URI="${IMAGE_TAG}"

gcloud builds submit . \
  --project="${PROJECT_ID}" \
  --config="${CLOUDBUILD}" \
  --substitutions=_IMAGE_URI="${IMAGE_TAG}"

echo ""
echo "Image construite. Pour relancer l'entraînement plus tard dans une nouvelle session :"
echo "  export IMAGE_URI=\"${IMAGE_URI}\""
