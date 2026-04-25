#!/usr/bin/env bash
# Recrée infra/gcp/cloudbuild_jarvis_train.yaml et submit_train_image.sh si absents
# (ZIP incomplet, oubli de fichiers à l’archivage, etc.).
#
# Usage typique depuis la racine du dépôt :
#   cd ~/jarvis_ai
#   bash infra/gcp/bootstrap_cloudbuild_assets.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_FROM_SCRIPT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -f "${REPO_FROM_SCRIPT}/pyproject.toml" ]] && [[ -f "${REPO_FROM_SCRIPT}/training/Dockerfile" ]]; then
  REPO_ROOT="${REPO_FROM_SCRIPT}"
elif [[ -f "./pyproject.toml" ]] && [[ -f "./training/Dockerfile" ]]; then
  REPO_ROOT="$(pwd -P)"
else
  echo "Erreur : place-toi dans la racine du projet (dossier avec pyproject.toml et training/), ex. :" >&2
  echo "  cd ~/jarvis_ai" >&2
  echo "puis relance : bash infra/gcp/bootstrap_cloudbuild_assets.sh" >&2
  exit 1
fi

cd "${REPO_ROOT}"
mkdir -p infra/gcp

if [[ ! -f infra/gcp/cloudbuild_jarvis_train.yaml ]]; then
  echo "Création de infra/gcp/cloudbuild_jarvis_train.yaml"
  cat > infra/gcp/cloudbuild_jarvis_train.yaml <<'YAML'
# Build de l'image d'entraînement Jarvis (Dockerfile dans training/).
# Depuis la racine du dépôt jarvis_ai :
#   export REGION=us-central1
#   export PROJECT_ID=votre-projet
#   export IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/jarvis/train:jarvis-mini-$(date +%Y%m%d)"
#   gcloud builds submit . --config=infra/gcp/cloudbuild_jarvis_train.yaml --substitutions=_IMAGE_URI="${IMAGE_TAG}"
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'training/Dockerfile'
      - '-t'
      - '${_IMAGE_URI}'
      - '.'
images:
  - '${_IMAGE_URI}'
timeout: 3600s
YAML
else
  echo "Déjà présent : infra/gcp/cloudbuild_jarvis_train.yaml"
fi

if [[ ! -f infra/gcp/submit_train_image.sh ]]; then
  echo "Création de infra/gcp/submit_train_image.sh"
  cat > infra/gcp/submit_train_image.sh <<'SH'
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
SH
  chmod +x infra/gcp/submit_train_image.sh
else
  echo "Déjà présent : infra/gcp/submit_train_image.sh"
fi

echo "Terminé. Vérifie : ls infra/gcp/cloudbuild_jarvis_train.yaml infra/gcp/submit_train_image.sh"
